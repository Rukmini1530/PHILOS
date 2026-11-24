"""Access-controlled dataset preview delivery."""

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from urllib.parse import quote

from app.config import settings
from app.services.storage import (
    StorageObjectNotFound,
    StorageUnavailableError,
    cloud_storage,
)


def dataset_preview_response(dataset):
    """Deliver local assets first; use checked public demo or private storage.

    The caller must authorize access to the dataset before calling this helper.
    """
    preview_path = settings.DATASETS_DIR / f"{dataset.id}_preview.jpg"
    if preview_path.is_file():
        return FileResponse(
            preview_path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400"
                if dataset.is_demo
                else "private, no-store",
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
            },
        )

    key = f"previews/{dataset.id}_preview.jpg"
    if dataset.is_demo:
        if not (cloud_storage.enabled and cloud_storage.public_url):
            raise HTTPException(status_code=404, detail="Preview not available")
        try:
            exists = cloud_storage.public_object_exists(key)
        except StorageUnavailableError:
            raise HTTPException(
                status_code=503, detail="Public preview storage is unavailable"
            ) from None
        if not exists:
            raise HTTPException(status_code=404, detail="Preview not available")
        version_time = dataset.updated_at or dataset.created_at
        version = (
            f"?v={quote(str(int(version_time.timestamp())))}"
            if version_time
            else ""
        )
        return RedirectResponse(
            url=f"{cloud_storage.public_url.rstrip('/')}/{key}{version}",
            status_code=302,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    metadata = dataset.extra_metadata or {}
    legacy_private_object = bool(metadata.get("preview_url") or metadata.get("tiles_uploaded_to_cloud"))
    if cloud_storage.private_enabled:
        try:
            obj = cloud_storage.private_object(key)
            return StreamingResponse(
                obj["Body"],
                media_type=obj.get("ContentType") or "image/jpeg",
                headers={"Cache-Control": "private, no-store"},
            )
        except StorageObjectNotFound:
            if legacy_private_object:
                raise HTTPException(
                    status_code=503,
                    detail="Legacy private preview requires operator-reviewed migration",
                ) from None
            raise HTTPException(status_code=404, detail="Preview not available") from None
        except StorageUnavailableError:
            raise HTTPException(
                status_code=503, detail="Private preview storage is unavailable"
            ) from None

    if any(
        metadata.get(field)
        for field in (
            "private_preview_uploaded",
            "private_tiles_uploaded_to_cloud",
            "tiles_uploaded_to_cloud",
            "preview_url",
        )
    ):
        raise HTTPException(
            status_code=503,
            detail="Private preview storage is not configured; local preview is unavailable",
        )
    raise HTTPException(status_code=404, detail="Preview not available")
