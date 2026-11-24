"""Deletion retry tests use temporary files and the isolated fixture database."""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Dataset
from app.services import cleanup
from app.services.dataset_processor import DatasetProcessor
from app.services.storage import StorageUnavailableError, cloud_storage


def make_dataset(db, name, tile_dir, source_file, *, metadata=None, expires=False):
    dataset = Dataset(
        name=name,
        description="temporary cleanup fixture",
        category="space",
        original_file_path=str(source_file),
        tile_base_path=str(tile_dir),
        width=16,
        height=16,
        min_zoom=0,
        max_zoom=1,
        tile_size=256,
        processing_status="completed",
        is_demo=False,
        extra_metadata=metadata or {},
        expires_at=datetime.utcnow() - timedelta(hours=1) if expires else None,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def prepare_local_assets(tmp_path, dataset_id):
    tile_dir = tmp_path / "tiles" / str(dataset_id)
    tile_dir.mkdir(parents=True)
    (tile_dir / "tile.png").write_bytes(b"temporary tile")
    source_file = tmp_path / f"{dataset_id}.tif"
    source_file.write_bytes(b"temporary source")
    preview_dir = tmp_path / "datasets"
    preview_dir.mkdir(exist_ok=True)
    (preview_dir / f"{dataset_id}_preview.jpg").write_bytes(b"temporary preview")
    return tile_dir, source_file, preview_dir


def test_local_deletion_failure_retains_dataset_and_retry_succeeds(
    database, tmp_path, monkeypatch
):
    dataset = make_dataset(database, "local-delete-retry", tmp_path / "tiles" / "1", tmp_path / "1.tif")
    tile_dir, source_file, preview_dir = prepare_local_assets(tmp_path, dataset.id)
    dataset.tile_base_path = str(tile_dir)
    dataset.original_file_path = str(source_file)
    database.commit()
    monkeypatch.setattr(cloud_storage, "enabled", False)
    monkeypatch.setattr(settings, "DATASETS_DIR", preview_dir)

    import shutil
    original_rmtree = shutil.rmtree

    def fail_local_delete(*_args, **_kwargs):
        raise PermissionError("isolated local deletion failure")

    monkeypatch.setattr(shutil, "rmtree", fail_local_delete)
    assert DatasetProcessor.delete_dataset(dataset.id, database) is False
    assert database.query(Dataset).filter_by(id=dataset.id).first() is not None
    assert source_file.exists()

    monkeypatch.setattr(shutil, "rmtree", original_rmtree)
    assert DatasetProcessor.delete_dataset(dataset.id, database) is True
    assert database.query(Dataset).filter_by(id=dataset.id).first() is None
    assert not tile_dir.exists()
    assert not source_file.exists()
    assert not (preview_dir / f"{dataset.id}_preview.jpg").exists()


def test_cloud_deletion_failure_retains_dataset_and_retry_is_idempotent(
    database, tmp_path, monkeypatch
):
    dataset = make_dataset(
        database,
        "cloud-delete-retry",
        tmp_path / "tiles" / "2",
        tmp_path / "2.tif",
        metadata={"private_tiles_uploaded_to_cloud": True},
    )
    tile_dir, source_file, preview_dir = prepare_local_assets(tmp_path, dataset.id)
    dataset.tile_base_path = str(tile_dir)
    dataset.original_file_path = str(source_file)
    database.commit()
    monkeypatch.setattr(settings, "DATASETS_DIR", preview_dir)
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(
        type(cloud_storage), "private_enabled", property(lambda _self: True)
    )
    calls = []

    def fail_cloud_delete(dataset_id, *, is_public):
        calls.append(("tiles", dataset_id, is_public))
        raise StorageUnavailableError("isolated storage failure")

    monkeypatch.setattr(cloud_storage, "delete_dataset_tiles", fail_cloud_delete)
    monkeypatch.setattr(
        cloud_storage,
        "delete_preview",
        lambda dataset_id, *, is_public: calls.append(("preview", dataset_id, is_public)) or True,
    )

    assert DatasetProcessor.delete_dataset(dataset.id, database) is False
    assert database.query(Dataset).filter_by(id=dataset.id).first() is not None
    assert tile_dir.exists()
    assert (preview_dir / f"{dataset.id}_preview.jpg").exists()
    assert calls == [("tiles", dataset.id, False)]

    monkeypatch.setattr(
        cloud_storage,
        "delete_dataset_tiles",
        lambda dataset_id, *, is_public: calls.append(("tiles-retry", dataset_id, is_public)) or 0,
    )
    assert DatasetProcessor.delete_dataset(dataset.id, database) is True
    assert database.query(Dataset).filter_by(id=dataset.id).first() is None
    assert calls[-2:] == [
        ("tiles-retry", dataset.id, False),
        ("preview", dataset.id, False),
    ]
    assert not (preview_dir / f"{dataset.id}_preview.jpg").exists()


def test_expiry_cleanup_keeps_row_after_failure_and_retries(
    database, tmp_path, monkeypatch
):
    dataset = make_dataset(
        database,
        "expiry-delete-retry",
        tmp_path / "tiles" / "3",
        tmp_path / "3.tif",
        metadata={"private_preview_uploaded": True},
        expires=True,
    )
    tile_dir, source_file, preview_dir = prepare_local_assets(tmp_path, dataset.id)
    dataset.tile_base_path = str(tile_dir)
    dataset.original_file_path = str(source_file)
    database.commit()
    dataset_id = dataset.id
    monkeypatch.setattr(settings, "DATASETS_DIR", preview_dir)
    cleanup_session_factory = sessionmaker(bind=database.get_bind())
    monkeypatch.setattr(cleanup, "SessionLocal", cleanup_session_factory)
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(
        type(cloud_storage), "private_enabled", property(lambda _self: True)
    )

    def fail_cloud_delete(*_args, **_kwargs):
        raise StorageUnavailableError("isolated storage failure")

    monkeypatch.setattr(cloud_storage, "delete_dataset_tiles", fail_cloud_delete)
    assert asyncio.run(cleanup.cleanup_expired_datasets()) == 0
    assert database.query(Dataset).filter_by(id=dataset_id).first() is not None
    assert tile_dir.exists()

    monkeypatch.setattr(cloud_storage, "delete_dataset_tiles", lambda *_a, **_k: 0)
    monkeypatch.setattr(cloud_storage, "delete_preview", lambda *_a, **_k: True)
    assert asyncio.run(cleanup.cleanup_expired_datasets()) == 1
    assert database.query(Dataset).filter_by(id=dataset_id).first() is None
    assert not tile_dir.exists()


def test_legacy_public_bucket_markers_block_private_dataset_deletion(
    database, tmp_path, monkeypatch
):
    for index, marker in enumerate(("tiles_uploaded_to_cloud", "preview_url"), 4):
        dataset = make_dataset(
            database,
            f"legacy-private-retained-{index}",
            tmp_path / "tiles" / str(index),
            tmp_path / f"{index}.tif",
            metadata={marker: True if marker != "preview_url" else "https://legacy.invalid/preview"},
        )
        monkeypatch.setattr(cloud_storage, "enabled", True)
        assert DatasetProcessor.delete_dataset(dataset.id, database) is False
        assert database.query(Dataset).filter_by(id=dataset.id).first() is not None
