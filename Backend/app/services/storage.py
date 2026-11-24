"""
Cloud Storage Service for Cloudflare R2 / AWS S3
Handles tile uploads and serving from cloud storage
"""

# LAZY IMPORTS: boto3 is only imported when actually needed to save ~50MB at startup
# import boto3
# from botocore.config import Config
# from botocore.exceptions import ClientError
from pathlib import Path
import logging
import os
from typing import Optional
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.config import settings

logger = logging.getLogger(__name__)


class StorageUnavailableError(Exception):
    """Configured storage could not safely serve the requested operation."""


class StorageObjectNotFound(Exception):
    """The requested cloud object does not exist."""


class CloudStorage:
    """
    Cloud storage service for tiles using S3-compatible APIs (Cloudflare R2, AWS S3)
    Uses lazy initialization to speed up app startup and save memory
    """
    
    def __init__(self):
        self.enabled = settings.USE_S3
        self._client = None  # Lazy initialization
        self._boto3 = None  # Lazy import
        self.bucket_name = settings.AWS_BUCKET_NAME
        self.private_bucket_name = settings.PRIVATE_S3_BUCKET_NAME.strip()
        self.private_access_confirmed = settings.PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED
        self.public_url = getattr(settings, 'R2_PUBLIC_URL', None) or ""
        self._initialized = False
        
        logger.info("CloudStorage configured: USE_S3=%s", settings.USE_S3)

    @property
    def private_enabled(self) -> bool:
        """Private cloud storage is enabled only by explicit operator opt-in."""
        return bool(
            self.enabled
            and self.private_access_confirmed
            and self.private_bucket_name
            and self.private_bucket_name.casefold() != self.bucket_name.strip().casefold()
        )

    def _bucket_name(self, is_public: bool) -> str:
        if is_public:
            return self.bucket_name.strip()
        if not self.private_enabled:
            return ""
        return self.private_bucket_name
    
    @property
    def client(self):
        """Lazy initialization of S3 client"""
        if self._client is None and self.enabled and not self._initialized:
            self._init_client()
        return self._client
    
    def _init_client(self):
        """Initialize S3/R2 client - imports boto3 only when needed"""
        try:
            # Lazy import boto3 to save memory at startup
            import boto3
            from botocore.config import Config
            
            # Get endpoint URL for R2 (not needed for AWS S3)
            endpoint_url = getattr(settings, 'S3_ENDPOINT_URL', None)
            
            config = Config(
                signature_version='s3v4',
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
            
            client_kwargs = {
                'service_name': 's3',
                'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                'config': config,
            }
            
            # Add endpoint URL for Cloudflare R2
            if endpoint_url:
                client_kwargs['endpoint_url'] = endpoint_url
                client_kwargs['region_name'] = 'auto'
            else:
                client_kwargs['region_name'] = settings.AWS_REGION
            
            self._client = boto3.client(**client_kwargs)
            self._initialized = True
            logger.info("Cloud storage initialized")
            
        except Exception:
            logger.error("Cloud storage client initialization failed")
            self._initialized = True  # Mark as initialized to prevent retry loops
            self.enabled = False
    
    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
        cache_control: str = "private, no-store",
        is_public: bool = False,
    ) -> bool:
        """
        Upload a file to cloud storage
        
        Args:
            local_path: Local file path
            remote_key: Remote object key (path in bucket)
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            True if successful
        """
        target_bucket = self._bucket_name(is_public)
        if not self.enabled or not target_bucket:
            logger.debug("Cloud storage disabled; upload skipped")
            return False
        
        # Ensure client is initialized
        if self.client is None:
            logger.error("Cloud storage client unavailable; upload skipped")
            return False
        
        try:
            if content_type is None:
                content_type, _ = mimetypes.guess_type(str(local_path))
                content_type = content_type or 'application/octet-stream'
            
            logger.debug("Uploading object to configured cloud storage")
            
            # Use put_object instead of upload_file for better error handling with R2
            with open(local_path, 'rb') as file_data:
                self.client.put_object(
                    Bucket=target_bucket,
                    Key=remote_key,
                    Body=file_data,
                    ContentType=content_type,
                    CacheControl=cache_control
                )
            
            logger.debug("Cloud object upload completed")
            return True
            
        except Exception:
            logger.error("Cloud object upload failed")
            return False
    
    def upload_tiles_directory(
        self,
        local_dir: Path,
        dataset_id: int,
        progress_callback=None,
        max_workers: int = None,
        is_public: bool = False,
    ) -> int:
        """
        Upload entire tiles directory to cloud storage using parallel uploads
        
        Args:
            local_dir: Local tiles directory (e.g., tiles/1/)
            dataset_id: Dataset ID for remote path prefix
            progress_callback: Optional callback(uploaded, total)
            max_workers: Number of parallel upload threads (default: 20)
            
        Returns:
            Number of files uploaded
        """
        if not self.enabled or not self._bucket_name(is_public):
            logger.warning(f"Cloud storage disabled, skipping tile upload for dataset {dataset_id}")
            return 0
        
        if not local_dir.exists():
            logger.error(f"Tiles directory not found: {local_dir}")
            return 0
        
        # Collect all files to upload
        files = [f for f in local_dir.rglob('*') if f.is_file()]
        total_files = len(files)
        
        if total_files == 0:
            logger.warning(f"No files found in {local_dir}")
            return 0
        
        # Use configured max_workers or default to 20
        if max_workers is None:
            max_workers = settings.R2_UPLOAD_MAX_WORKERS
        
        logger.info(f"📤 Starting parallel tile upload: {total_files} files with {max_workers} workers for dataset {dataset_id}")
        start_time = time.time()
        
        uploaded = 0
        failed = 0
        
        def upload_single_tile(file_path: Path) -> tuple[bool, str]:
            """Upload a single tile and return (success, filename)"""
            try:
                relative_path = file_path.relative_to(local_dir)
                remote_key = f"tiles/{dataset_id}/{relative_path}".replace("\\", "/")
                cache_control = (
                    "public, max-age=31536000"
                    if is_public
                    else "private, no-store"
                )
                success = self.upload_file(
                    file_path,
                    remote_key,
                    cache_control=cache_control,
                    is_public=is_public,
                )
                return (success, file_path.name)
            except Exception:
                logger.error("Cloud tile upload failed")
                return (False, file_path.name)
        
        # Use ThreadPoolExecutor for parallel uploads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {executor.submit(upload_single_tile, f): f for f in files}
            
            # Process completed uploads
            for future in as_completed(future_to_file):
                success, filename = future.result()
                if success:
                    uploaded += 1
                else:
                    failed += 1
                    logger.warning(f"Failed to upload tile: {filename}")
                
                # Report progress every 100 files or at key milestones
                if uploaded % 100 == 0 or uploaded == total_files:
                    elapsed = time.time() - start_time
                    rate = uploaded / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {uploaded}/{total_files} tiles ({rate:.1f} tiles/sec)")
                    
                if progress_callback:
                    progress_callback(uploaded, total_files)
        
        elapsed_time = time.time() - start_time
        rate = uploaded / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f"✅ Uploaded {uploaded}/{total_files} tiles to R2 for dataset {dataset_id}")
        logger.info(f"⏱️  Upload completed in {elapsed_time:.1f}s ({rate:.1f} tiles/sec, {failed} failed)")
        
        return uploaded
    
    def get_tile_url(
        self,
        dataset_id: int,
        z: int,
        x: int,
        y: int,
        format: str = 'jpg',
        version: Optional[str] = None,
        is_public: bool = False,
    ) -> Optional[str]:
        """
        Get public URL for a tile
        
        Args:
            dataset_id: Dataset ID
            z, x, y: Tile coordinates
            format: Image format
            
        Returns:
            Public URL or None if not using cloud storage
        """
        if not is_public or not self.enabled or not self.public_url:
            return None
        
        url = f"{self.public_url}/tiles/{dataset_id}/{z}/{x}/{y}.{format}"
        if version:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}v={version}"
        return url
    
    def tile_exists(self, dataset_id: int, z: int, x: int, y: int, format: str = 'jpg') -> bool:
        """Check if a tile exists in cloud storage"""
        if not self.enabled:
            return False
        
        try:
            key = f"tiles/{dataset_id}/{z}/{x}/{y}.{format}"
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def private_object(self, key: str):
        """Fetch an object only from the explicitly configured private bucket."""
        if not self.private_enabled:
            raise StorageUnavailableError("Private cloud storage is not configured")
        client = self.client
        if client is None:
            raise StorageUnavailableError("Private cloud storage is unavailable")
        try:
            return client.get_object(Bucket=self.private_bucket_name, Key=key)
        except Exception as exc:
            code = None
            try:
                code = exc.response.get("Error", {}).get("Code")
            except Exception:
                pass
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise StorageObjectNotFound from None
            raise StorageUnavailableError("Private cloud storage request failed") from None

    def public_object_exists(self, key: str) -> bool:
        """Check a public/demo object, distinguishing absent from failed storage."""
        if not self.enabled or not self.bucket_name:
            raise StorageUnavailableError("Public cloud storage is unavailable")
        client = self.client
        if client is None:
            raise StorageUnavailableError("Public cloud storage is unavailable")
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            code = None
            try:
                code = exc.response.get("Error", {}).get("Code")
            except Exception:
                pass
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise StorageUnavailableError("Public cloud storage request failed") from None
    
    def delete_dataset_tiles(self, dataset_id: int, is_public: bool = False) -> int:
        """
        Delete all tiles for a dataset from cloud storage
        
        Returns:
            Number of objects deleted
        """
        target_bucket = self._bucket_name(is_public)
        if not self.enabled:
            return 0
        if not target_bucket:
            raise StorageUnavailableError("Configured dataset storage is unavailable")
        
        try:
            client = self.client
            if client is None:
                raise StorageUnavailableError("Configured dataset storage is unavailable")
            deleted = 0
            prefix = f"tiles/{dataset_id}/"
            
            # List and delete in batches
            paginator = client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=target_bucket, Prefix=prefix):
                if 'Contents' not in page:
                    continue
                
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                
                if objects:
                    result = client.delete_objects(
                        Bucket=target_bucket,
                        Delete={'Objects': objects}
                    )
                    if result.get("Errors"):
                        raise StorageUnavailableError("Cloud tile deletion was incomplete")
                    deleted += len(objects)
            
            logger.info(f"Deleted {deleted} tiles for dataset {dataset_id}")
            return deleted
            
        except StorageUnavailableError:
            raise
        except Exception:
            logger.error("Cloud tile deletion failed for dataset %s", dataset_id)
            raise StorageUnavailableError("Cloud tile deletion failed") from None

    def delete_preview(self, dataset_id: int, is_public: bool = False) -> bool:
        target_bucket = self._bucket_name(is_public)
        if not self.enabled:
            return False
        if not target_bucket:
            raise StorageUnavailableError("Configured preview storage is unavailable")
        try:
            client = self.client
            if client is None:
                raise StorageUnavailableError("Configured preview storage is unavailable")
            client.delete_object(
                Bucket=target_bucket,
                Key=f"previews/{dataset_id}_preview.jpg",
            )
            return True
        except StorageUnavailableError:
            raise
        except Exception:
            logger.warning("Failed to delete dataset preview from cloud storage")
            raise StorageUnavailableError("Cloud preview deletion failed") from None
    
    def upload_preview(
        self,
        local_path: Path,
        dataset_id: int,
        version: Optional[str] = None,
        is_public: bool = False,
    ) -> Optional[str]:
        """
        Upload dataset preview image
        
        Returns:
            Public URL of the preview or None
        """
        if not self.enabled:
            logger.debug(f"Cloud storage disabled, skipping preview upload")
            return None
        
        if not local_path.exists():
            logger.warning("Dataset preview file is not available locally")
            return None
        
        remote_key = f"previews/{dataset_id}_preview.jpg"
        
        logger.info(f"📤 Uploading preview for dataset {dataset_id}")
        if not is_public:
            self.upload_private_preview(local_path, dataset_id)
            return None
        cache_control = "public, max-age=86400"
        if self.upload_file(
            local_path,
            remote_key,
            "image/jpeg",
            cache_control=cache_control,
            is_public=True,
        ):
            if is_public and self.public_url:
                preview_url = f"{self.public_url}/{remote_key}"
                if version:
                    preview_url = f"{preview_url}?v={version}"
                logger.info("Dataset preview uploaded to cloud storage")
                return preview_url
        
        logger.error(f"Failed to upload preview for dataset {dataset_id}")
        return None

    def upload_private_preview(self, local_path: Path, dataset_id: int) -> bool:
        if not self.private_enabled or not local_path.exists():
            return False
        return self.upload_file(
            local_path,
            f"previews/{dataset_id}_preview.jpg",
            "image/jpeg",
            cache_control="private, no-store",
            is_public=False,
        )

    def save_dataset_metadata(self, dataset_dict: dict) -> bool:
        """
        Save dataset metadata to R2 as JSON for persistence
        
        Args:
            dataset_dict: Dataset data as dictionary
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            import json
            import tempfile
            
            dataset_id = dataset_dict.get('id')
            if not dataset_id:
                return False
            
            # Save individual dataset metadata
            json_data = json.dumps(dataset_dict, default=str)
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=f"metadata/datasets/{dataset_id}.json",
                Body=json_data.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Saved metadata for dataset {dataset_id} to R2")
            return True
            
        except Exception:
            logger.error("Cloud dataset metadata save failed")
            return False
    
    def load_all_datasets_metadata(self) -> list:
        """
        Load all dataset metadata from R2
        
        Returns:
            List of dataset dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            import json
            
            datasets = []
            prefix = "metadata/datasets/"
            
            paginator = self.client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    try:
                        response = self.client.get_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
                        data = json.loads(response['Body'].read().decode('utf-8'))
                        datasets.append(data)
                    except Exception:
                        logger.error("Failed to load a public demo metadata object")
            
            logger.info(f"✅ Loaded {len(datasets)} datasets from R2 metadata")
            return datasets
            
        except Exception:
            logger.error("Failed to load public demo metadata")
            return []
    
    def delete_dataset_metadata(self, dataset_id: int) -> bool:
        """Delete dataset metadata from R2"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=f"metadata/datasets/{dataset_id}.json"
            )
            logger.info(f"✅ Deleted metadata for dataset {dataset_id}")
            return True
        except Exception:
            logger.error("Failed to delete public demo metadata")
            return False


# Global instance
cloud_storage = CloudStorage()
