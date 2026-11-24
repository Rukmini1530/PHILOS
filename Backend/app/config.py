"""
Configuration management for NASA Gigapixel Explorer API
"""

from pydantic_settings import BaseSettings
from pydantic import ValidationError, field_validator, model_validator, Field
from sqlalchemy.engine import make_url
from pathlib import Path
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "NASA Gigapixel Explorer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Set to False for production
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    # Database configuration is required explicitly to avoid implicit connections.
    DATABASE_URL: str
    SQLALCHEMY_POOL_SIZE: int = Field(20, env="SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = Field(10, env="SQLALCHEMY_MAX_OVERFLOW")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Storage - Base directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TILES_DIR: Path = BASE_DIR / "tiles"
    DATASETS_DIR: Path = BASE_DIR / "datasets"
    TEMP_DIR: Path = BASE_DIR / "temp"

    # Tile Settings
    TILE_SIZE: int = 256
    TILE_FORMAT: str = "jpg"
    TILE_QUALITY: int = 85
    MAX_ZOOM: int = 20
    GDAL_PROCESSES: int = 4

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Upload
    MAX_UPLOAD_SIZE: int = 42949672960  # 40GB
    MAX_REQUEST_BODY_SIZE: int = 42949672960  # 40GB (for Starlette)

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Cloud Storage (Cloudflare R2 / AWS S3)
    USE_S3: bool = False
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "auto"  # Use 'auto' for R2
    S3_ENDPOINT_URL: str = ""  # R2 endpoint: https://<account_id>.r2.cloudflarestorage.com
    R2_UPLOAD_MAX_WORKERS: int = 20  # Parallel upload threads (10-50 recommended, 10 for HF Spaces)
    R2_PUBLIC_URL: str = ""  # Public bucket URL: https://pub-xxxx.r2.dev
    PRIVATE_S3_BUCKET_NAME: str = ""
    PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED: bool = False

    @field_validator("USE_S3", mode="before")
    @classmethod
    def parse_use_s3(cls, v):
        """Parse USE_S3 from string/bool"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must be configured.")
        try:
            parsed_url = make_url(value)
        except Exception:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy database URL.") from None
        if not parsed_url.drivername:
            raise ValueError("DATABASE_URL must include a database driver.")
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        weak_markers = ("change-this", "change_me", "your-secret", "replace-with", "changeme")
        if len(value) < 32 or len(set(value)) < 16 or any(marker in normalized for marker in weak_markers):
            raise ValueError("SECRET_KEY must be a strong, externally supplied value of at least 32 characters.")
        return value

    @model_validator(mode="after")
    def validate_private_storage_separation(self):
        private_bucket = self.PRIVATE_S3_BUCKET_NAME.strip()
        public_bucket = self.AWS_BUCKET_NAME.strip()
        if (
            self.PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED
            and not private_bucket
        ):
            raise ValueError(
                "PRIVATE_S3_BUCKET_NAME is required when private bucket access is confirmed."
            )
        if (
            self.PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED
            and private_bucket.casefold() == public_bucket.casefold()
        ):
            raise ValueError(
                "The private storage bucket must be distinct from AWS_BUCKET_NAME."
            )
        return self

    @property
    def DB_HOST(self) -> str:
        """Expose the configured host for existing operator tooling."""
        return make_url(self.DATABASE_URL).host or "local"

    @property
    def DB_NAME(self) -> str:
        """Expose the configured database name without exposing credentials."""
        return make_url(self.DATABASE_URL).database or ""

    model_config = {
        # Load from .env if it exists, but environment variables take priority
        # HF Spaces uses environment variables (secrets), not .env file
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "hide_input_in_errors": True,
        # Validate on assignment to catch issues early
        "validate_assignment": True,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        for directory in [
            self.UPLOAD_DIR,
            self.TILES_DIR,
            self.DATASETS_DIR,
            self.TEMP_DIR,
        ]:
            directory.mkdir(exist_ok=True, parents=True)


# Create global settings instance. Keep configuration failures clear while
# avoiding Pydantic's default error rendering, which can include input values.
try:
    settings = Settings()
except ValidationError:
    raise RuntimeError(
        "Invalid application configuration. Set DATABASE_URL to a valid database URL "
        "and SECRET_KEY to a strong value of at least 32 characters. Verify private storage "
        "configuration uses a distinct bucket before enabling private cloud storage."
    ) from None


def get_settings() -> Settings:
    """Get settings instance"""
    return settings
