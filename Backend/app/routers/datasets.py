"""
Dataset management endpoints
"""

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Query,
    HTTPException,
    BackgroundTasks,
    Form,
    Response,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pathlib import Path
import asyncio
import logging
import shutil
import re
import aiofiles
import uuid
import os

from datetime import datetime, timedelta

from app.database import get_db
from app.models import Annotation, Dataset, User
from app.schemas import (
    DatasetCreate,
    DatasetResponse,
    DatasetDetail,
    DatasetUpdate,
    MessageResponse,
    ProcessingStatus,
    DatasetStats,
)
from app.services.storage import cloud_storage
from app.services.dataset_processor import DatasetProcessor
from app.services.cleanup import get_time_until_expiry, reset_database_sequences
from app.services.auth import (
    get_current_superuser,
    get_current_user,
    get_current_user_required,
)
from app.services.authorization import (
    accessible_datasets,
    get_accessible_dataset,
    require_dataset_write_access,
)
from app.services.previews import dataset_preview_response
from app.config import settings

# Optimized chunk size for fast uploads (8MB chunks)
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

# Store for tracking chunked uploads
chunked_uploads = {}
UPLOAD_SESSION_TTL = timedelta(hours=24)


def _remove_chunked_upload(upload_id: str, session: dict) -> None:
    chunked_uploads.pop(upload_id, None)
    root = settings.TEMP_DIR.resolve()
    temp_dir = Path(session["temp_dir"]).resolve()
    if temp_dir.parent == root:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _purge_expired_chunked_uploads() -> None:
    now = datetime.utcnow()
    for upload_id, session in list(chunked_uploads.items()):
        if session["expires_at"] <= now:
            _remove_chunked_upload(upload_id, session)


def _get_owned_chunked_upload(upload_id: str, current_user: User) -> dict:
    try:
        uuid.UUID(upload_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=404, detail="Upload session not found") from None

    session = chunked_uploads.get(upload_id)
    if session is None or session["owner_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session["expires_at"] <= datetime.utcnow():
        _remove_chunked_upload(upload_id, session)
        raise HTTPException(status_code=410, detail="Upload session expired")
    return session

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_DATASET_EXTENSIONS = {".tif", ".tiff", ".psb", ".psd"}


def validate_upload_filename(filename: Optional[str]) -> str:
    """Accept only a plain supported filename, never a client-supplied path."""
    if not filename or len(filename) > 255 or "\x00" in filename:
        raise HTTPException(status_code=400, detail="Invalid dataset filename")
    if "/" in filename or "\\" in filename or ":" in filename:
        raise HTTPException(status_code=400, detail="Invalid dataset filename")
    if Path(filename).name != filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid dataset filename")
    if Path(filename).suffix.lower() not in ALLOWED_DATASET_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Supported: .tif, .tiff, .psb, .psd",
        )
    return filename


# This route handles /datasets/{id}_preview.jpg requests
# Must be defined in main.py BEFORE the static mount to work
preview_router = APIRouter()


@preview_router.get("/datasets/{dataset_id}_preview.jpg")
async def get_dataset_preview(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Return a dataset preview after checking dataset visibility."""
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    return dataset_preview_response(dataset)


# ============================================================================
# CHUNKED UPLOAD ENDPOINTS - For large files (10GB+)
# ============================================================================

@router.post("/datasets/upload/init")
async def init_chunked_upload(
    filename: str = Query(..., description="Original filename"),
    filesize: int = Query(..., ge=1, description="Total file size in bytes"),
    total_chunks: int = Query(..., ge=1, description="Total number of chunks"),
    current_user: User = Depends(get_current_user_required),
):
    """
    Initialize a chunked upload session for large files.
    Returns an upload_id to use for subsequent chunk uploads.
    """
    filename = validate_upload_filename(filename)
    
    # Enforce file size limit
    if filesize > settings.MAX_UPLOAD_SIZE:
        max_gb = settings.MAX_UPLOAD_SIZE / (1024**3)
        size_gb = filesize / (1024**3)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_gb:.1f}GB (you requested {size_gb:.1f}GB)",
        )

    expected_chunks = (filesize + UPLOAD_CHUNK_SIZE - 1) // UPLOAD_CHUNK_SIZE
    if total_chunks != expected_chunks:
        raise HTTPException(status_code=400, detail="Invalid total chunk count")

    _purge_expired_chunked_uploads()

    # Generate unique upload ID
    upload_id = str(uuid.uuid4())
    
    # Create temp directory for chunks
    temp_root = settings.TEMP_DIR.resolve()
    temp_dir = (temp_root / upload_id).resolve()
    if temp_dir.parent != temp_root:
        raise HTTPException(status_code=400, detail="Invalid upload session path")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Store upload session info
    chunked_uploads[upload_id] = {
        "filename": filename,
        "filesize": filesize,
        "total_chunks": total_chunks,
        "owner_id": current_user.id,
        "expires_at": datetime.utcnow() + UPLOAD_SESSION_TTL,
        "state": "active",
        "lock": asyncio.Lock(),
        "received_chunks": set(),
        "temp_dir": temp_dir,
    }
    
    logger.info("Initialized chunked dataset upload for user %s", current_user.id)
    
    return {
        "upload_id": upload_id,
        "chunk_size": UPLOAD_CHUNK_SIZE,
        "expires_at": chunked_uploads[upload_id]["expires_at"].isoformat(),
        "message": "Upload initialized. Send chunks to /api/datasets/upload/chunk"
    }


@router.post("/datasets/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(..., ge=0),
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
):
    """
    Upload a single chunk of a large file.
    """
    session = _get_owned_chunked_upload(upload_id, current_user)
    async with session["lock"]:
        session = _get_owned_chunked_upload(upload_id, current_user)
        if session["state"] != "active":
            raise HTTPException(status_code=409, detail="Upload session is not active")
        if chunk_index >= session["total_chunks"]:
            raise HTTPException(status_code=400, detail="Chunk index is out of range")

        expected_size = min(
            UPLOAD_CHUNK_SIZE,
            session["filesize"] - chunk_index * UPLOAD_CHUNK_SIZE,
        )
        if chunk.size is not None and chunk.size != expected_size:
            raise HTTPException(status_code=400, detail="Chunk size does not match upload plan")

        content = await chunk.read(expected_size + 1)
        if len(content) > expected_size:
            raise HTTPException(status_code=413, detail="Chunk exceeds expected size")
        if len(content) != expected_size:
            raise HTTPException(status_code=400, detail="Chunk is incomplete")

        chunk_path = Path(session["temp_dir"]) / f"chunk_{chunk_index:06d}"
        try:
            async with aiofiles.open(chunk_path, "wb") as chunk_file:
                await chunk_file.write(content)
        except Exception:
            logger.error("Failed to store an upload chunk")
            raise HTTPException(status_code=500, detail="Failed to store upload chunk") from None

        session["received_chunks"].add(chunk_index)
        received = len(session["received_chunks"])
        total = session["total_chunks"]
        return {
            "chunk_index": chunk_index,
            "received": received,
            "total": total,
            "complete": received == total,
        }


@router.post("/datasets/upload/complete", response_model=DatasetResponse)
async def complete_chunked_upload(
    background_tasks: BackgroundTasks,
    upload_id: str = Query(...),
    name: str = Query(..., description="Dataset name"),
    description: Optional[str] = Query(None),
    category: str = Query(..., pattern="^(earth|mars|space)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Assemble and process a chunk upload owned by the authenticated user."""
    session = _get_owned_chunked_upload(upload_id, current_user)
    async with session["lock"]:
        session = _get_owned_chunked_upload(upload_id, current_user)
        if session["state"] != "active":
            raise HTTPException(status_code=409, detail="Upload session is not active")
        if len(session["received_chunks"]) != session["total_chunks"]:
            missing = session["total_chunks"] - len(session["received_chunks"])
            raise HTTPException(
                status_code=400,
                detail=f"Upload incomplete. Missing {missing} chunks.",
            )
        for index in range(session["total_chunks"]):
            if not (Path(session["temp_dir"]) / f"chunk_{index:06d}").is_file():
                raise HTTPException(status_code=400, detail="Upload contains a missing chunk")
        session["state"] = "completing"

    upload_root = settings.UPLOAD_DIR.resolve()
    final_path = (upload_root / f"{upload_id}_{session['filename']}").resolve()
    if final_path.parent != upload_root:
        _remove_chunked_upload(upload_id, session)
        raise HTTPException(status_code=400, detail="Invalid upload destination")

    assembled_size = 0
    try:
        async with aiofiles.open(final_path, "wb") as output_file:
            for index in range(session["total_chunks"]):
                chunk_path = Path(session["temp_dir"]) / f"chunk_{index:06d}"
                expected_chunk_size = min(
                    UPLOAD_CHUNK_SIZE,
                    session["filesize"] - index * UPLOAD_CHUNK_SIZE,
                )
                chunk_size = 0
                async with aiofiles.open(chunk_path, "rb") as input_file:
                    while content := await input_file.read(UPLOAD_CHUNK_SIZE):
                        chunk_size += len(content)
                        assembled_size += len(content)
                        if chunk_size > expected_chunk_size or assembled_size > session["filesize"]:
                            raise HTTPException(status_code=400, detail="Upload size validation failed")
                        await output_file.write(content)
                if chunk_size != expected_chunk_size:
                    raise HTTPException(status_code=400, detail="Upload contains an invalid chunk")
        if assembled_size != session["filesize"]:
            raise HTTPException(status_code=400, detail="Assembled file size does not match upload plan")
    except HTTPException:
        if final_path.exists():
            final_path.unlink()
        _remove_chunked_upload(upload_id, session)
        raise
    except Exception:
        if final_path.exists():
            final_path.unlink()
        _remove_chunked_upload(upload_id, session)
        logger.error("Failed to assemble chunked upload")
        raise HTTPException(status_code=500, detail="Failed to assemble upload") from None

    _remove_chunked_upload(upload_id, session)
    dataset_info = DatasetCreate(name=name, description=description, category=category)
    try:
        dataset = await DatasetProcessor.create_dataset_entry(final_path, dataset_info, db)
        dataset.owner_id = current_user.id
        dataset.is_demo = False
        dataset.expires_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        db.refresh(dataset)
    except ValueError as exc:
        db.rollback()
        if final_path.exists():
            final_path.unlink()
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception:
        db.rollback()
        if final_path.exists():
            final_path.unlink()
        logger.error("Failed to register chunked dataset upload")
        raise HTTPException(status_code=500, detail="Failed to create dataset") from None

    background_tasks.add_task(
        DatasetProcessor.process_tiles_background,
        dataset.id,
        final_path,
    )
    logger.info("Created chunked dataset %s for user %s", dataset.id, current_user.id)
    return dataset


@router.delete("/datasets/upload/{upload_id}")
async def cancel_chunked_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user_required),
):
    """Cancel and clean up a chunked upload session."""
    session = _get_owned_chunked_upload(upload_id, current_user)
    async with session["lock"]:
        session = _get_owned_chunked_upload(upload_id, current_user)
        if session["state"] != "active":
            raise HTTPException(status_code=409, detail="Upload session is not active")
        _remove_chunked_upload(upload_id, session)
    
    return {"message": "Upload cancelled and cleaned up"}


# ============================================================================
# REGULAR UPLOAD ENDPOINT
# ============================================================================

@router.post("/datasets/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Query(..., description="Dataset name"),
    description: Optional[str] = Query(None, description="Dataset description"),
    category: str = Query(
        ..., description="Dataset category", pattern="^(earth|mars|space)$"
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_required),
):
    """
    Upload and process a new dataset

    - **file**: Image file (.tif, .tiff, .psb, .psd) - Supports GeoTIFF and Photoshop Big formats
    - **name**: Unique dataset name
    - **description**: Optional description
    - **category**: Dataset category (earth, mars, or space)
    """
    safe_filename = validate_upload_filename(file.filename)

    # Check file size (40GB limit - supports large PSB files up to 25GB+)
    if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE:
        size_gb = file.size / (1024**3)
        max_gb = settings.MAX_UPLOAD_SIZE / (1024**3)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_gb:.1f}GB (you uploaded {size_gb:.1f}GB)",
        )

    # Save uploaded file with optimized async streaming
    file_path = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_filename}"
    try:
        # Use async file writing with large chunks for speed
        async with aiofiles.open(file_path, "wb") as buffer:
            uploaded_size = 0
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                uploaded_size += len(chunk)
                if uploaded_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=413, detail="File exceeds upload limit")
                await buffer.write(chunk)
        if uploaded_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        logger.info("Saved uploaded dataset file")
    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")

    # Create dataset info
    dataset_info = DatasetCreate(name=name, description=description, category=category)

    # Create dataset entry immediately (with pending status)
    try:
        dataset = await DatasetProcessor.create_dataset_entry(file_path, dataset_info, db)
        
        # Set owner and expiry for user uploads (not demo datasets)
        dataset.owner_id = current_user.id
        dataset.is_demo = False
        dataset.expires_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        db.refresh(dataset)
        
        # Start background tile generation (pass dataset.id, not db session)
        background_tasks.add_task(
            DatasetProcessor.process_tiles_background,
            dataset.id,
            file_path
        )
        
        logger.info(f"Dataset {dataset.id} created by user {current_user.id}, expires at {dataset.expires_at}")
        return dataset
        
    except ValueError as e:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail="Error creating dataset")


@router.post("/datasets/from-folder", response_model=MessageResponse)
async def process_folder_datasets(
    folder_path: str = Query(..., description="Path to folder containing .tif files"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    Process all GeoTIFF files from a specified folder

    - **folder_path**: Path to folder containing .tif files
    """
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder path")

    # Find all .tif and .psb files
    tif_files = list(folder.glob("*.tif")) + list(folder.glob("*.tiff"))
    tif_files += list(folder.glob("*.TIF")) + list(folder.glob("*.TIFF"))
    tif_files += list(folder.glob("*.psb")) + list(folder.glob("*.PSB"))

    if not tif_files:
        raise HTTPException(status_code=400, detail="No .tif or .psb files found in folder")

    processed_count = 0
    failed_count = 0

    for tif_file in tif_files:
        # Auto-detect category from filename
        filename_lower = tif_file.stem.lower()
        if any(
            word in filename_lower for word in ["earth", "landsat", "modis", "sentinel"]
        ):
            category = "earth"
        elif any(word in filename_lower for word in ["mars", "hirise", "ctx"]):
            category = "mars"
        elif any(
            word in filename_lower for word in ["messier", "ngc", "galaxy", "nebula"]
        ):
            category = "space"
        else:
            category = "space"  # Default

        dataset_info = DatasetCreate(
            name=tif_file.stem,
            description=f"Auto-imported from {tif_file.name}",
            category=category,
        )

        try:
            dataset = await DatasetProcessor.process_dataset(tif_file, dataset_info, db)
            processed_count += 1
            logger.info(f"Processed dataset: {dataset.name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to process {tif_file.name}: {e}")

    return MessageResponse(
        message=f"Processed {processed_count} datasets successfully",
        detail=f"{failed_count} failed" if failed_count > 0 else None,
    )


@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    List datasets with caching for better performance:
    - Authenticated users: Only their own datasets
    - Guest users: Only demo datasets (is_demo=True)
    - Short cache (5 min) to balance freshness vs performance

    - **category**: Filter by category (earth, mars, space)
    - **status**: Filter by processing status (pending, processing, completed, failed)
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    """
    query = accessible_datasets(db, current_user)

    if category:
        query = query.filter(Dataset.category == category)

    if status:
        query = query.filter(Dataset.processing_status == status)

    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate time_until_expiry for datasets expiring within 1 hour
    result = []
    for dataset in datasets:
        dataset_dict = DatasetResponse.model_validate(dataset).model_dump()
        
        # Add time until expiry if dataset expires within 1 hour
        if dataset.expires_at:
            now = datetime.utcnow()
            time_left = (dataset.expires_at - now).total_seconds()
            if 0 < time_left <= 3600:  # Show only if expiring within 1 hour
                dataset_dict['time_until_expiry'] = get_time_until_expiry(dataset.expires_at)
        
        result.append(DatasetResponse(**dataset_dict))
    
    return result


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get detailed information about a specific dataset

    - **dataset_id**: ID of the dataset
    """
    return get_accessible_dataset(db, dataset_id, current_user)


@router.get("/datasets/{dataset_id}/tile-status")
async def get_tile_fetch_status(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get the tile fetching status for a dataset
    
    Returns whether all tiles have been fetched and processed from R2/local storage.
    Frontend uses this to determine when to stop showing loading animation.

    - **dataset_id**: ID of the dataset
    
    Response:
    - **tiles_ready**: Boolean indicating if all tiles are ready for rendering
    - **processing_status**: Current processing status (pending, processing, completed, failed)
    - **tiles_on_cloud**: Whether tiles have been uploaded to R2
    - **message**: Human-readable status message
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)

    # Determine if tiles are ready
    cloud_marker = (
        "tiles_uploaded_to_cloud"
        if dataset.is_demo
        else "private_tiles_uploaded_to_cloud"
    )
    tiles_on_cloud = bool(
        dataset.extra_metadata and dataset.extra_metadata.get(cloud_marker)
    )
    
    tiles_ready = dataset.processing_status == "completed"
    
    status_message = {
        "pending": "Waiting to process tiles",
        "processing": "Processing tiles from source...",
        "completed": "All tiles ready for rendering",
        "failed": "Tile processing failed"
    }.get(dataset.processing_status, "Unknown status")

    return {
        "tiles_ready": tiles_ready,
        "processing_status": dataset.processing_status,
        "tiles_on_cloud": tiles_on_cloud,
        "message": status_message,
        "dataset_id": dataset_id
    }


@router.put("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int, 
    dataset_update: DatasetUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    Update dataset metadata
    
    Restrictions:
    - Only the owner can update their dataset
    - Demo datasets cannot be modified

    - **dataset_id**: ID of the dataset
    - **dataset_update**: Fields to update
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    
    require_dataset_write_access(dataset, current_user)

    # Update fields
    if dataset_update.name is not None:
        dataset.name = dataset_update.name
    if dataset_update.description is not None:
        dataset.description = dataset_update.description
    if dataset_update.category is not None:
        dataset.category = dataset_update.category

    db.commit()
    db.refresh(dataset)

    return dataset


@router.delete("/datasets/{dataset_id}", response_model=MessageResponse)
async def delete_dataset(
    dataset_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    Delete dataset and associated tiles
    
    Restrictions:
    - Only the owner can delete their dataset
    - Demo datasets cannot be deleted by anyone

    - **dataset_id**: ID of the dataset to delete
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    
    require_dataset_write_access(dataset, current_user)
    
    success = DatasetProcessor.delete_dataset(dataset_id, db)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to delete dataset"
        )
    
    # Reset database sequences to prevent ID gaps after deletion
    reset_database_sequences(db)

    return MessageResponse(message=f"Dataset {dataset_id} deleted successfully")


@router.get("/datasets/{dataset_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get dataset processing status

    - **dataset_id**: ID of the dataset
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)

    return ProcessingStatus(
        status=dataset.processing_status,
        message=f"Dataset is {dataset.processing_status}",
        progress=1.0 if dataset.processing_status == "completed" else 0.0,
    )


@router.post("/datasets/{dataset_id}/reprocess", response_model=MessageResponse)
async def reprocess_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """
    Regenerate tiles for an existing dataset

    - **dataset_id**: ID of the dataset to reprocess
    """
    dataset = get_accessible_dataset(db, dataset_id, current_user)
    require_dataset_write_access(dataset, current_user)
    success = DatasetProcessor.reprocess_dataset(dataset_id, db)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reprocess dataset")

    return MessageResponse(message=f"Dataset {dataset_id} reprocessing started")


@router.get("/stats", response_model=DatasetStats)
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None,
):
    """
    Get overall dataset statistics
    """
    visible = accessible_datasets(db, current_user)
    if response is not None and visible.filter(Dataset.is_demo.is_(False)).count():
        response.headers["Cache-Control"] = "private, no-store"
    visible_ids = visible.with_entities(Dataset.id)
    total_datasets = visible.count()
    datasets_by_category = {
        category: visible.filter(Dataset.category == category).count()
        for category in ("earth", "mars", "space")
    }
    total_pixels = (
        db.query(func.sum(Dataset.width * Dataset.height))
        .filter(Dataset.id.in_(visible_ids))
        .scalar()
        or 0
    )
    total_annotations = (
        db.query(Annotation).filter(Annotation.dataset_id.in_(visible_ids)).count()
    )

    return DatasetStats(
        total_datasets=total_datasets,
        datasets_by_category=datasets_by_category,
        total_annotations=total_annotations,
        total_storage_size=total_pixels * 3,  # Rough estimate
    )
