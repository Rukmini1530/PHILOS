"""Storage metadata tests using a local fake S3 client only."""

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.services.storage import CloudStorage, cloud_storage


class FakeS3Client:
    def __init__(self):
        self.objects = []

    def put_object(self, **kwargs):
        self.objects.append(kwargs)


def test_ordinary_test_configuration_cannot_enable_cloud_storage():
    assert settings.USE_S3 is False
    assert cloud_storage.enabled is False
    assert cloud_storage.private_enabled is False
    assert cloud_storage.private_bucket_name == ""
    assert cloud_storage.private_access_confirmed is False


def test_private_preview_upload_is_not_published_as_public_url(tmp_path):
    client = FakeS3Client()
    storage = CloudStorage()
    storage.enabled = True
    storage._client = client
    storage._initialized = True
    storage.bucket_name = "isolated-test-bucket"
    storage.private_bucket_name = "isolated-private-test-bucket"
    storage.private_access_confirmed = True
    storage.public_url = "https://storage.invalid"
    preview = tmp_path / "preview.jpg"
    preview.write_bytes(b"test-preview")

    result = storage.upload_preview(preview, dataset_id=17, is_public=False)

    assert result is None
    assert len(client.objects) == 1
    assert client.objects[0]["Bucket"] == "isolated-private-test-bucket"
    assert client.objects[0]["Key"] == "previews/17_preview.jpg"
    assert client.objects[0]["CacheControl"] == "private, no-store"


def test_demo_preview_upload_returns_public_url_and_cache_policy(tmp_path):
    client = FakeS3Client()
    storage = CloudStorage()
    storage.enabled = True
    storage._client = client
    storage._initialized = True
    storage.bucket_name = "isolated-test-bucket"
    storage.private_bucket_name = "isolated-private-test-bucket"
    storage.private_access_confirmed = True
    storage.public_url = "https://storage.invalid"
    preview = tmp_path / "preview.jpg"
    preview.write_bytes(b"demo-preview")

    result = storage.upload_preview(
        preview, dataset_id=18, version="fixture", is_public=True
    )

    assert result == "https://storage.invalid/previews/18_preview.jpg?v=fixture"
    assert client.objects[0]["Bucket"] == "isolated-test-bucket"
    assert client.objects[0]["CacheControl"] == "public, max-age=86400"


def test_private_tile_upload_uses_private_cache_metadata(tmp_path):
    client = FakeS3Client()
    storage = CloudStorage()
    storage.enabled = True
    storage._client = client
    storage._initialized = True
    storage.bucket_name = "isolated-test-bucket"
    storage.private_bucket_name = "isolated-private-test-bucket"
    storage.private_access_confirmed = True
    tile = tmp_path / "0" / "0" / "0.png"
    tile.parent.mkdir(parents=True)
    tile.write_bytes(b"tile")

    uploaded = storage.upload_tiles_directory(
        tmp_path, dataset_id=19, max_workers=1, is_public=False
    )

    assert uploaded == 1
    assert client.objects[0]["Bucket"] == "isolated-private-test-bucket"
    assert client.objects[0]["Key"] == "tiles/19/0/0/0.png"
    assert client.objects[0]["CacheControl"] == "private, no-store"


def test_private_storage_requires_explicit_access_confirmation():
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket_name = "public-test-bucket"
    storage.private_bucket_name = "private-test-bucket"
    storage.private_access_confirmed = False

    assert storage.private_enabled is False


def test_private_storage_rejects_the_public_bucket_name():
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket_name = "shared-test-bucket"
    storage.private_bucket_name = "shared-test-bucket"
    storage.private_access_confirmed = True

    assert storage.private_enabled is False


def test_private_upload_stays_local_when_private_bucket_is_not_configured(tmp_path):
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket_name = "public-test-bucket"
    storage.private_bucket_name = ""
    storage.private_access_confirmed = False
    preview = tmp_path / "preview.jpg"
    preview.write_bytes(b"local-preview")

    assert storage.upload_private_preview(preview, dataset_id=20) is False


def test_configuration_rejects_confirming_the_public_bucket_as_private():
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="sqlite://",
            SECRET_KEY="test-only-distinct-random-secret-value-1234567890",
            AWS_BUCKET_NAME="same-test-bucket",
            PRIVATE_S3_BUCKET_NAME="same-test-bucket",
            PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED=True,
        )


def test_public_preview_head_check_distinguishes_missing_from_storage_failure():
    class FakeClientError(Exception):
        def __init__(self, code):
            self.response = {"Error": {"Code": code}}

    class FakeS3Client:
        def __init__(self, outcome):
            self.outcome = outcome

        def head_object(self, **_kwargs):
            if isinstance(self.outcome, Exception):
                raise self.outcome
            return {}

    storage = CloudStorage()
    storage.enabled = True
    storage.bucket_name = "isolated-demo-bucket"
    storage._client = FakeS3Client({})
    assert storage.public_object_exists("previews/demo_preview.jpg") is True

    storage._client = FakeS3Client(FakeClientError("404"))
    assert storage.public_object_exists("previews/missing_preview.jpg") is False

    from app.services.storage import StorageUnavailableError

    storage._client = FakeS3Client(FakeClientError("AccessDenied"))
    with pytest.raises(StorageUnavailableError):
        storage.public_object_exists("previews/restricted_preview.jpg")


def test_public_tile_url_builder_requires_explicit_public_asset():
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket_name = "isolated-demo-bucket"
    storage.public_url = "https://assets.invalid"

    assert storage.get_tile_url(42, 0, 0, 0) is None
    assert storage.get_tile_url(42, 0, 0, 0, is_public=True) == (
        "https://assets.invalid/tiles/42/0/0/0.jpg"
    )
