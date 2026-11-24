"""
Automatic cleanup service for expired datasets
Removes datasets older than 24 hours and their associated files
"""

import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import SessionLocal
from app.models import Dataset
from app.services.storage import cloud_storage
from app.config import settings

logger = logging.getLogger(__name__)


async def delete_dataset_files(dataset: Dataset) -> bool:
    """
    Delete all files associated with a dataset
    
    Args:
        dataset: Dataset model instance
        
    Returns:
        True if successful
    """
    try:
        metadata = dataset.extra_metadata or {}
        if not dataset.is_demo and (
            metadata.get("tiles_uploaded_to_cloud") or metadata.get("preview_url")
        ):
            logger.warning(
                "Dataset %s has legacy private assets requiring operator review",
                dataset.id,
            )
            return False

        if not dataset.is_demo and not cloud_storage.private_enabled and any(
            metadata.get(field)
            for field in (
                "private_tiles_uploaded_to_cloud",
                "private_preview_uploaded",
            )
        ):
            logger.warning(
                "Private storage is unavailable for cleanup of dataset %s", dataset.id
            )
            return False

        # Remote deletion is idempotent. Attempt it before local deletion so a
        # failed cloud operation leaves every local retry source intact.
        if not dataset.is_demo and cloud_storage.private_enabled:
            await asyncio.to_thread(
                cloud_storage.delete_dataset_tiles, dataset.id, is_public=False
            )
            await asyncio.to_thread(
                cloud_storage.delete_preview, dataset.id, is_public=False
            )

        # Delete local tiles directory
        tiles_dir = Path(dataset.tile_base_path)
        if not tiles_dir.is_absolute():
            tiles_dir = settings.BASE_DIR / tiles_dir
        if tiles_dir.exists():
            import shutil
            shutil.rmtree(tiles_dir, ignore_errors=True)
            if tiles_dir.exists():
                raise OSError("Local tile directory deletion failed")
            logger.info(f"Deleted local tiles for dataset {dataset.id}")
        
        # Delete uploaded file
        upload_path = Path(dataset.original_file_path)
        if not upload_path.is_absolute():
            upload_path = settings.BASE_DIR / upload_path
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
            logger.info(f"Deleted upload file for dataset {dataset.id}")
        
        # Delete preview thumbnail if exists
        preview_path = settings.DATASETS_DIR / f"{dataset.id}_preview.jpg"
        if preview_path.exists():
            preview_path.unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete files for dataset {dataset.id}: {e}")
        return False


async def cleanup_expired_datasets() -> int:
    """
    Find and delete all expired datasets
    
    Returns:
        Number of datasets deleted
    """
    db = SessionLocal()
    deleted_count = 0
    
    try:
        # Find all expired non-demo datasets
        now = datetime.utcnow()
        expired_datasets = db.query(Dataset).filter(
            and_(
                Dataset.is_demo == False,
                Dataset.expires_at != None,
                Dataset.expires_at <= now
            )
        ).all()
        
        logger.info(f"Found {len(expired_datasets)} expired datasets to cleanup")
        
        for dataset in expired_datasets:
            try:
                # Keep the row as the retry record unless every asset cleanup
                # operation completed successfully.
                if not await delete_dataset_files(dataset):
                    raise RuntimeError("Dataset asset cleanup failed; row retained for retry")
                
                # Delete from database
                db.delete(dataset)
                db.commit()
                
                deleted_count += 1
                logger.info(f"✅ Deleted expired dataset: {dataset.name} (ID: {dataset.id})")
                
            except Exception as e:
                logger.error(f"Failed to delete dataset {dataset.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"Cleanup complete: {deleted_count} datasets deleted")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        db.rollback()
        return deleted_count
        
    finally:
        db.close()


async def cleanup_scheduler():
    """
    Background task that runs cleanup every hour
    """
    logger.info("🧹 Starting cleanup scheduler (runs every hour)")
    
    while True:
        try:
            # Run cleanup
            deleted = await cleanup_expired_datasets()
            
            if deleted > 0:
                logger.info(f"✨ Cleanup job completed: {deleted} datasets removed")
            
            # Wait 1 hour before next run
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
            # Wait 5 minutes before retry on error
            await asyncio.sleep(300)


def get_time_until_expiry(expires_at: datetime) -> str:
    """
    Calculate human-readable time remaining until expiry
    
    Args:
        expires_at: Expiry timestamp
        
    Returns:
        Human-readable string like "23 hours" or "45 minutes"
    """
    if not expires_at:
        return None
    
    now = datetime.utcnow()
    delta = expires_at - now
    
    if delta.total_seconds() <= 0:
        return "Expired"
    
    # Calculate time components
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return "Less than a minute"


def reset_database_sequences(db: Session) -> bool:
    """
    Reset database sequences to prevent ID gaps after deletions.
    
    For PostgreSQL: Resets the dataset_id_seq sequence to MAX(id) + 1
    For SQLite: No-op (SQLite handles this automatically with AUTOINCREMENT)
    
    Args:
        db: Database session
        
    Returns:
        True if successful
    """
    try:
        # Get the maximum dataset ID
        from sqlalchemy import func
        max_id = db.query(func.max(Dataset.id)).scalar()
        
        if max_id is None:
            max_id = 0
        
        # For PostgreSQL, reset the sequence
        try:
            db.execute(f"SELECT setval('datasets_id_seq', {max_id + 1})")
            db.commit()
            logger.info(f"✅ Reset database sequence to {max_id + 1}")
            return True
        except Exception as e:
            # If sequence reset fails (SQLite, different schema), just log and continue
            logger.debug(f"Could not reset sequence (expected on SQLite): {e}")
            return True
            
    except Exception as e:
        logger.error(f"Error resetting database sequences: {e}")
        return False
