"""
Tile serving endpoints with R2 optimization
"""

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Query
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse, Response
from sqlalchemy.orm import Session
from pathlib import Path
import logging
from typing import Optional, List
import asyncio

from app.database import get_db
from app.models import Dataset, User
from app.config import settings
from app.services.storage import (
    cloud_storage,
    StorageObjectNotFound,
    StorageUnavailableError,
)
from app.services.auth import get_current_user
from app.services.authorization import get_accessible_dataset
from app.services.r2_tile_cache import tile_cache
from app.services.previews import dataset_preview_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tiles/{dataset_id}/batch")
async def get_tiles_batch(
    dataset_id: int = PathParam(..., description="Dataset ID"),
    tiles: List[str] = Query(..., description="Tile coordinates as z/x/y.format"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None,
):
    """
    Fetch multiple tiles in parallel from R2 with caching
    
    Performance features:
    - Connection pooling with HTTP/2 multiplexing
    - LRU in-memory cache for hot tiles
    - Parallel fetches (up to 50 concurrent)
    - ~100x faster than sequential requests
    
    Example: GET /api/tiles/1/batch?tiles=0/0/0.jpg&tiles=1/2/3.png
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    # A batch belongs to exactly one dataset ID, so its contents cannot mix
    # public demo and private user assets.
    if not dataset.is_demo and response is not None:
        response.headers["Cache-Control"] = "private, no-store"

    if dataset.is_demo and not (tile_cache.enabled and tile_cache.public_url):
        return {"error": "Public tile cache is not configured", "tiles": {}}
    
    tile_list = []
    for tile_coord in tiles[:100]:
        try:
            parts = tile_coord.split('/')
            if len(parts) == 3:
                z = int(parts[0])
                x = int(parts[1])
                y_format = parts[2].split('.')
                if len(y_format) == 2:
                    y = int(y_format[0])
                    fmt = y_format[1].lower()
                    if (
                        z >= 0
                        and x >= 0
                        and y >= 0
                        and fmt in {"jpg", "jpeg", "png", "webp"}
                    ):
                        tile_list.append((dataset_id, z, x, y, fmt))
        except (ValueError, IndexError):
            continue
    
    if tile_list:
        logger.info(f"📥 Thread pool fetch {len(tile_list)} tiles, dataset {dataset_id}")
        if not dataset.is_demo:
            import base64

            tile_data = {}
            for _, z, x, y, fmt in tile_list:
                key = f"tiles/{dataset_id}/{z}/{x}/{y}.{fmt}"
                data = None
                if (
                    cloud_storage.private_enabled
                    and dataset.extra_metadata
                    and dataset.extra_metadata.get("private_tiles_uploaded_to_cloud")
                ):
                    try:
                        obj = cloud_storage.private_object(key)
                        data = obj["Body"].read()
                    except StorageObjectNotFound:
                        pass
                    except StorageUnavailableError:
                        raise HTTPException(
                            status_code=503,
                            detail="Private tile storage is unavailable",
                            headers={"Cache-Control": "private, no-store"},
                        ) from None
                if data is None:
                    tile_base = Path(dataset.tile_base_path)
                    if not tile_base.is_absolute():
                        tile_base = settings.BASE_DIR / tile_base
                    local_tile = tile_base / str(z) / str(x) / f"{y}.{fmt}"
                    if not local_tile.is_file() and fmt in {"jpg", "jpeg"}:
                        local_tile = tile_base / str(z) / str(x) / f"{y}.png"
                    if local_tile.is_file():
                        data = local_tile.read_bytes()
                if data:
                    tile_data[f"{z}/{x}/{y}.{fmt}"] = base64.b64encode(data).decode()
            return {
                "dataset_id": dataset_id,
                "count": len(tile_data),
                "tiles": tile_data,
            }

        # Use high-speed thread pool instead of async
        results = tile_cache.fetch_tiles_parallel_sync(tile_list, is_public=True)
        
        import base64
        tile_data = {}
        for key, data in results.items():
            if data:
                tile_data[key] = base64.b64encode(data).decode()
        
        return {
            "dataset_id": dataset_id,
            "count": len(tile_data),
            "tiles": tile_data,
            "cache_stats": tile_cache.get_cache_stats()
        }
    
    return {"tiles": {}}


@router.get("/tiles/{dataset_id}/cache-stats")
async def get_cache_stats(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None,
):
    """Get R2 cache performance stats"""
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    if not dataset.is_demo and response is not None:
        response.headers["Cache-Control"] = "private, no-store"
    return {
        "dataset_id": dataset_id,
        "stats": tile_cache.get_cache_stats()
    }


@router.get("/tiles/{dataset_id}/prefetch/{z}")
async def prefetch_level_tiles(
    dataset_id: int = PathParam(..., description="Dataset ID"),
    z: int = PathParam(..., ge=0, le=30, description="Zoom level to prefetch"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None,
):
    """
    Prefetch all tiles at a specific zoom level (optimized for levels 4-7)
    
    Returns metadata about the level without loading full tiles.
    Frontend can then selectively load tiles as needed.
    
    - **dataset_id**: ID of the dataset
    - **z**: Zoom level (recommended for 4-7 for small tiles)
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    if not dataset.is_demo and response is not None:
        response.headers["Cache-Control"] = "private, no-store"
    
    # Calculate tile grid for this zoom level
    tile_size = dataset.tile_size or 256
    tiles_x = (dataset.width >> z) // tile_size + 1
    tiles_y = (dataset.height >> z) // tile_size + 1
    
    # For high levels (4-7), provide full tile list for aggressive caching
    is_high_level = 4 <= z <= 7
    
    return {
        "dataset_id": dataset_id,
        "level": z,
        "tiles_x": tiles_x,
        "tiles_y": tiles_y,
        "total_tiles": tiles_x * tiles_y,
        "is_high_level": is_high_level,
        "recommended_batch_size": 50 if is_high_level else 20,
        "cache_aggressively": is_high_level,
    }


@router.get("/tiles/{dataset_id}/{z}/{x}/{y}.{format}")
async def get_tile(
    dataset_id: int = PathParam(..., description="Dataset ID"),
    z: int = PathParam(..., ge=0, le=30, description="Zoom level"),
    x: int = PathParam(..., ge=0, description="Tile X coordinate"),
    y: int = PathParam(..., ge=0, description="Tile Y coordinate"),
    format: str = PathParam(..., pattern="^(jpg|png|webp)$", description="Tile format"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Serve individual tiles for a dataset
    
    Access control:
    - Demo datasets: Anyone can access
    - User datasets: Only the owner can access

    - **dataset_id**: ID of the dataset
    - **z**: Zoom level (0 = furthest out)
    - **x**: Tile X coordinate
    - **y**: Tile Y coordinate
    - **format**: Image format (jpg, png, webp)
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    tile_cache_control = (
        "public, max-age=31536000, immutable"
        if dataset.is_demo
        else "private, no-store"
    )

    # Allow serving tiles if completed OR if tiles exist locally (processing might be stuck)
    if dataset.processing_status not in ["completed", "processing"]:
        raise HTTPException(
            status_code=503, detail=f"Dataset is {dataset.processing_status}"
        )

    # Cache-busting token to avoid stale tiles when dataset IDs get reused
    cache_bust = None
    if dataset.updated_at:
        cache_bust = str(int(dataset.updated_at.timestamp()))
    elif dataset.created_at:
        cache_bust = str(int(dataset.created_at.timestamp()))

    # Check in-memory cache first (FAST - microseconds)
    if tile_cache.enabled:
        cached_tile = tile_cache.get_cached_tile(dataset_id, z, x, y, format)
        if cached_tile:
            logger.info(f"💾 Serving from cache: {dataset_id}/{z}/{x}/{y}.{format}")
            return Response(
                content=cached_tile,
                media_type=f"image/{format}",
                headers={
                    "Cache-Control": tile_cache_control,
                    "X-Tile-Source": "memory-cache",
                    "Access-Control-Allow-Origin": "*",
                }
            )

    # If cloud storage (R2) is enabled, check if tiles have been uploaded
    # Try metadata flag first, then check R2 directly for datasets synced from cloud
    private_tiles_uploaded = bool(
        dataset.extra_metadata
        and dataset.extra_metadata.get("private_tiles_uploaded_to_cloud")
    )
    private_storage_failed = False
    if not dataset.is_demo and private_tiles_uploaded and cloud_storage.private_enabled:
        key = f"tiles/{dataset_id}/{z}/{x}/{y}.{format}"
        try:
            obj = cloud_storage.private_object(key)
            return StreamingResponse(
                obj["Body"],
                media_type=obj.get("ContentType") or f"image/{format}",
                headers={
                    "Cache-Control": "private, no-store",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        except StorageObjectNotFound:
            pass
        except StorageUnavailableError:
            private_storage_failed = True
            logger.warning("Private tile storage is unavailable")

    if dataset.is_demo and cloud_storage.enabled and cloud_storage.public_url:
        logger.debug(f"R2 check: dataset={dataset_id}/{z}/{x}/{y}.{format}")
        
        # Check if tiles have been uploaded to R2 (metadata flag)
        tiles_on_r2 = (
            dataset.extra_metadata and 
            dataset.extra_metadata.get('tiles_uploaded_to_cloud') == True
        )
        
        # If flag not set, check R2 directly (for datasets synced from cloud)
        if not tiles_on_r2:
            logger.debug(f"Checking R2 directly...")
            tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, format)
            
            # If exact format not found, try alternatives
            if not tiles_on_r2:
                if format.lower() in ["jpg", "jpeg"]:
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "png")
                    if tiles_on_r2:
                        format = "png"
                elif format.lower() == "png":
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "jpg")
                    if tiles_on_r2:
                        format = "jpg"
        
        if tiles_on_r2:
            # Try proxying through backend to add CORS headers; fall back to redirect
            key = f"tiles/{dataset_id}/{z}/{x}/{y}.{format}"
            if cloud_storage.client:
                try:
                    obj = cloud_storage.client.get_object(Bucket=cloud_storage.bucket_name, Key=key)
                    body = obj["Body"]
                    content_type = obj.get("ContentType") or f"image/{format}"
                    headers = {
                        "Cache-Control": tile_cache_control,
                        "Access-Control-Allow-Origin": "*",
                    }
                    logger.debug(f"Streaming R2: {key}")
                    return StreamingResponse(body, media_type=content_type, headers=headers)
                except Exception:
                    logger.debug("Public demo tile proxy failed")

            tile_url = (
                cloud_storage.get_tile_url(
                    dataset_id, z, x, y, format, cache_bust, is_public=True
                )
                if dataset.is_demo
                else None
            )
            if tile_url:
                logger.info(f"🔗 Serving tile from R2 via redirect: {dataset_id}/{z}/{x}/{y}.{format} → {tile_url}")
                return RedirectResponse(
                    url=tile_url,
                    status_code=302,
                    headers={
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*",
                    }
                )

        # If we get here and cloud storage is enabled, log that we're falling back to local
        if cloud_storage.enabled:
            logger.warning(f"❌ Tile not found on R2 for dataset {dataset_id}/{z}/{x}/{y}.{format}, checking local storage")

    # Validate zoom level
    if z > dataset.max_zoom:
        raise HTTPException(
            status_code=400, detail=f"Zoom level {z} exceeds maximum {dataset.max_zoom}"
        )

    # Construct tile path
    # Handle both relative and absolute paths
    if Path(dataset.tile_base_path).is_absolute():
        tile_base = Path(dataset.tile_base_path)
    else:
        # Relative path - make it relative to TILES_DIR or BASE_DIR
        tile_base = settings.BASE_DIR / dataset.tile_base_path

    tile_path = tile_base / str(z) / str(x) / f"{y}.{format}"

    # If requested format doesn't exist, try fallback formats
    if not tile_path.exists():
        # Try alternative formats (PNG if JPG requested, JPG if PNG requested)
        fallback_formats = []
        if format.lower() == "jpg" or format.lower() == "jpeg":
            fallback_formats = ["png", "webp"]
        elif format.lower() == "png":
            fallback_formats = ["jpg", "jpeg", "webp"]
        elif format.lower() == "webp":
            fallback_formats = ["png", "jpg", "jpeg"]
        
        # Try fallback formats
        for fallback_format in fallback_formats:
            fallback_path = tile_base / str(z) / str(x) / f"{y}.{fallback_format}"
            if fallback_path.exists():
                logger.info(
                    f"Tile {z}/{x}/{y} requested as {format} but found as {fallback_format}, serving fallback"
                )
                tile_path = fallback_path
                format = fallback_format  # Update format for media type
                break
        else:
            legacy_cloud_asset = bool(
                dataset.extra_metadata
                and dataset.extra_metadata.get("tiles_uploaded_to_cloud")
            )
            if (
                not dataset.is_demo
                and (
                    private_storage_failed
                    or (legacy_cloud_asset and not private_tiles_uploaded)
                    or ((legacy_cloud_asset or private_tiles_uploaded) and not cloud_storage.private_enabled)
                )
            ):
                raise HTTPException(
                    status_code=503,
                    detail="Private tile storage is not configured; local tile is unavailable",
                )
            # No fallback found, return 404
            raise HTTPException(
                status_code=404,
                detail=f"Tile {z}/{x}/{y} not found for dataset {dataset_id} (tried: {format}, {', '.join(fallback_formats)})"
            )

    # Serve tile with caching headers
    # Normalize media type (jpg/jpeg -> jpeg)
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    media_type = media_type_map.get(format.lower(), f"image/{format}")
    
    # ULTRA-optimize headers for high-level tiles (4-7) - small and frequently accessed
    is_high_level = 4 <= z <= 7
    
    # Different caching strategy for high-level tiles
    if dataset.is_demo and is_high_level:
        # Aggressive caching for small tiles
        cache_control = "public, max-age=31536000, immutable, stale-while-revalidate=604800"
        # Additional performance headers for small tiles
        extra_headers = {
            "X-High-Level-Tile": "true",
            "X-Tile-Size": "small",
            "Priority": "u=2, i",  # High priority hint for browsers
        }
    elif dataset.is_demo:
        cache_control = "public, max-age=31536000, immutable"
        extra_headers = {}
    else:
        cache_control = "private, no-store"
        extra_headers = {}

    return FileResponse(
        tile_path,
        media_type=media_type,
        headers={
            "Cache-Control": cache_control,
            "X-Tile-Status": "exists",
            "X-Tile-Format": format,
            "X-Tile-Level": str(z),
            "Access-Control-Allow-Origin": "*",
            "Cross-Origin-Resource-Policy": "cross-origin",
            "Vary": "Accept-Encoding",
            **extra_headers,  # Add high-level specific headers
        },
    )


@router.get("/tiles/{dataset_id}/preview")
async def get_preview(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get preview thumbnail for a dataset

    - **dataset_id**: ID of the dataset
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)

    return dataset_preview_response(dataset)

@router.get("/tiles/{dataset_id}/info")
async def get_tile_info(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None,
):
    """
    Get tile metadata for OpenSeadragon configuration

    - **dataset_id**: ID of the dataset
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    if not dataset.is_demo and response is not None:
        response.headers["Cache-Control"] = "private, no-store"

    # Return OpenSeadragon-compatible tile source info
    return {
        "type": "zoomify",
        "width": dataset.width,
        "height": dataset.height,
        "tileSize": dataset.tile_size,
        "minZoom": dataset.min_zoom,
        "maxZoom": dataset.max_zoom,
        "tilesUrl": f"{settings.API_PREFIX}/tiles/{dataset_id}/{{z}}/{{x}}/{{y}}.png",
        "profile": "level0",
        "bounds": (
            dataset.extra_metadata.get("bounds") if dataset.extra_metadata else None
        ),
    }
