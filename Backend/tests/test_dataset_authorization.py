from app.models import Dataset, User
from app.services.auth import get_password_hash
from app.config import settings
from app.routers.tiles import cloud_storage, tile_cache
from app.middleware.cache import response_cache


def add_user(db, email, username, password, *, is_superuser=False):
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_dataset(db, name, *, owner=None, demo=False):
    dataset = Dataset(
        name=name,
        description=f"Description for {name}",
        category="space",
        owner_id=owner.id if owner else None,
        original_file_path=f"{name}.tif",
        tile_base_path=f"tiles/{name}",
        width=2048,
        height=1024,
        min_zoom=0,
        max_zoom=4,
        tile_size=256,
        processing_status="completed",
        is_demo=demo,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_listing_shows_demo_and_own_datasets_only(client, database, login_token):
    owner = add_user(database, "owner-list@example.invalid", "ownerlist", "test-owner-password")
    other = add_user(database, "other-list@example.invalid", "otherlist", "test-other-password")
    demo = add_dataset(database, "list-demo", demo=True)
    own = add_dataset(database, "list-own", owner=owner)
    add_dataset(database, "list-other", owner=other)

    anonymous = client.get("/api/datasets")
    assert {row["id"] for row in anonymous.json()} == {demo.id}

    token = login_token(owner.email, "test-owner-password")
    authenticated = client.get("/api/datasets", headers=auth_header(token))
    assert {row["id"] for row in authenticated.json()} == {demo.id, own.id}


def test_dataset_detail_status_and_tile_info_follow_visibility(
    client, database, login_token
):
    owner = add_user(database, "owner-detail@example.invalid", "ownerdetail", "test-owner-password")
    other = add_user(database, "other-detail@example.invalid", "otherdetail", "test-other-password")
    demo = add_dataset(database, "detail-demo", demo=True)
    private = add_dataset(database, "detail-private", owner=owner)
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")

    assert client.get(f"/api/datasets/{demo.id}").status_code == 200
    assert client.get(f"/api/datasets/{private.id}").status_code == 404
    assert client.get(
        f"/api/datasets/{private.id}", headers=auth_header(owner_token)
    ).status_code == 200
    assert client.get(
        f"/api/datasets/{private.id}/status", headers=auth_header(other_token)
    ).status_code == 404
    assert client.get(
        f"/api/tiles/{private.id}/info", headers=auth_header(other_token)
    ).status_code == 404

    owned_status = client.get(
        f"/api/datasets/{private.id}/status", headers=auth_header(owner_token)
    )
    assert owned_status.status_code == 200
    assert owned_status.headers["cache-control"] == "private, no-store"
    for path in (
        f"/api/tiles/{private.id}/info",
        f"/api/tiles/{private.id}/prefetch/1",
        f"/api/tiles/{private.id}/cache-stats",
    ):
        response = client.get(path, headers=auth_header(owner_token))
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"


def test_private_tile_batch_is_no_store_and_demo_batch_remains_public(
    client, database, login_token, monkeypatch, tmp_path
):
    owner = add_user(database, "batch-owner@example.invalid", "batchowner", "test-batch-password")
    private = add_dataset(database, "batch-private", owner=owner)
    demo = add_dataset(database, "batch-demo", demo=True)
    private_tile_dir = tmp_path / "private-tiles"
    tile_path = private_tile_dir / "0" / "0" / "0.png"
    tile_path.parent.mkdir(parents=True)
    tile_path.write_bytes(b"private-tile")
    private.tile_base_path = str(private_tile_dir)
    database.commit()
    token = login_token(owner.email, "test-batch-password")
    monkeypatch.setattr(cloud_storage, "enabled", False)
    monkeypatch.setattr(tile_cache, "enabled", False)

    private_response = client.get(
        f"/api/tiles/{private.id}/batch",
        params={"tiles": "0/0/0.png"},
        headers=auth_header(token),
    )
    assert private_response.status_code == 200
    assert private_response.headers["cache-control"] == "private, no-store"

    public_response = client.get(
        f"/api/tiles/{demo.id}/batch", params={"tiles": "0/0/0.png"}
    )
    assert public_response.status_code == 200
    assert "cache-control" not in public_response.headers


def test_private_dataset_detail_cache_never_crosses_principals(
    client, database, login_token
):
    owner = add_user(database, "cache-owner@example.invalid", "cacheowner", "test-cache-owner")
    other = add_user(database, "cache-other@example.invalid", "cacheother", "test-cache-other")
    private = add_dataset(database, "cache-private", owner=owner)
    owner_token = login_token(owner.email, "test-cache-owner")
    other_token = login_token(other.email, "test-cache-other")

    owner_response = client.get(
        f"/api/datasets/{private.id}", headers=auth_header(owner_token)
    )
    assert owner_response.status_code == 200
    assert owner_response.headers["cache-control"] == "private, no-store"

    assert client.get(
        f"/api/datasets/{private.id}", headers=auth_header(other_token)
    ).status_code == 404
    assert client.get(f"/api/datasets/{private.id}").status_code == 404
    assert response_cache == {}


def test_private_dataset_lists_are_not_shared_between_users(
    client, database, login_token
):
    owner = add_user(database, "list-cache-owner@example.invalid", "listcacheowner", "test-list-owner")
    other = add_user(database, "list-cache-other@example.invalid", "listcacheother", "test-list-other")
    demo = add_dataset(database, "cache-list-demo", demo=True)
    own = add_dataset(database, "cache-list-own", owner=owner)
    other_private = add_dataset(database, "cache-list-other", owner=other)
    owner_token = login_token(owner.email, "test-list-owner")
    other_token = login_token(other.email, "test-list-other")

    owner_response = client.get("/api/datasets", headers=auth_header(owner_token))
    other_response = client.get("/api/datasets", headers=auth_header(other_token))
    anonymous_response = client.get("/api/datasets")

    assert owner_response.headers["cache-control"] == "private, no-store"
    assert {row["id"] for row in owner_response.json()} == {demo.id, own.id}
    other_visible_ids = {row["id"] for row in other_response.json()}
    assert other_visible_ids == {demo.id, other_private.id}
    assert own.id not in other_visible_ids
    assert {row["id"] for row in anonymous_response.json()} == {demo.id}
    assert response_cache == {}


def test_foreign_user_cannot_update_delete_or_reprocess_dataset(
    client, database, login_token
):
    owner = add_user(database, "owner-write@example.invalid", "ownerwrite", "test-owner-password")
    other = add_user(database, "other-write@example.invalid", "otherwrite", "test-other-password")
    private = add_dataset(database, "write-private", owner=owner)
    token = login_token(other.email, "test-other-password")
    headers = auth_header(token)

    assert client.put(
        f"/api/datasets/{private.id}",
        headers=headers,
        json={"description": "attempted update"},
    ).status_code == 404
    assert client.delete(f"/api/datasets/{private.id}", headers=headers).status_code == 404
    assert client.post(f"/api/datasets/{private.id}/reprocess", headers=headers).status_code == 404
    database.refresh(private)
    assert private.description == "Description for write-private"


def test_demo_datasets_are_public_read_only_for_ordinary_users(
    client, database, login_token
):
    user = add_user(database, "demo-user@example.invalid", "demouser", "test-demo-password")
    demo = add_dataset(database, "public-demo-dataset", demo=True)
    token = login_token(user.email, "test-demo-password")
    headers = auth_header(token)

    assert client.get(f"/api/datasets/{demo.id}").status_code == 200
    assert client.put(
        f"/api/datasets/{demo.id}",
        headers=headers,
        json={"description": "not allowed"},
    ).status_code == 403
    assert client.delete(f"/api/datasets/{demo.id}", headers=headers).status_code == 403
    assert client.post(f"/api/datasets/{demo.id}/reprocess", headers=headers).status_code == 403


def test_statistics_are_scoped_to_visible_datasets(client, database, login_token):
    owner = add_user(database, "owner-stats@example.invalid", "ownerstats", "test-owner-password")
    other = add_user(database, "other-stats@example.invalid", "otherstats", "test-other-password")
    add_dataset(database, "stats-demo", demo=True)
    add_dataset(database, "stats-owner", owner=owner)
    add_dataset(database, "stats-private", owner=other)
    token = login_token(owner.email, "test-owner-password")

    response = client.get("/api/stats", headers=auth_header(token))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["total_datasets"] == 2


def test_preview_route_hides_private_previews_and_serves_public_demo(
    client, database, login_token, tmp_path, monkeypatch
):
    owner = add_user(database, "owner-preview@example.invalid", "ownerpreview", "test-owner-password")
    other = add_user(database, "other-preview@example.invalid", "otherpreview", "test-other-password")
    demo = add_dataset(database, "preview-demo", demo=True)
    private = add_dataset(database, "preview-private", owner=owner)
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(cloud_storage, "enabled", False)
    (tmp_path / f"{demo.id}_preview.jpg").write_bytes(b"demo-preview")
    (tmp_path / f"{private.id}_preview.jpg").write_bytes(b"private-preview")
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")

    assert client.get(f"/datasets/{demo.id}_preview.jpg").content == b"demo-preview"
    assert client.get(f"/datasets/{private.id}_preview.jpg").status_code == 404
    assert client.get(
        f"/datasets/{private.id}_preview.jpg", headers=auth_header(other_token)
    ).status_code == 404
    assert client.get(
        f"/datasets/{private.id}_preview.jpg", headers=auth_header(owner_token)
    ).content == b"private-preview"


def test_tile_preview_public_demo_private_owner_and_foreign_denial(
    client, database, login_token, tmp_path, monkeypatch
):
    owner = add_user(database, "owner-tile-preview@example.invalid", "ownertilepreview", "test-owner-password")
    other = add_user(database, "other-tile-preview@example.invalid", "othertilepreview", "test-other-password")
    demo = add_dataset(database, "tile-preview-demo", demo=True)
    private = add_dataset(database, "tile-preview-private", owner=owner)
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(cloud_storage, "enabled", False)
    (tmp_path / f"{demo.id}_preview.jpg").write_bytes(b"public-demo-preview")
    (tmp_path / f"{private.id}_preview.jpg").write_bytes(b"private-preview")
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")

    demo_response = client.get(f"/api/tiles/{demo.id}/preview")
    assert demo_response.status_code == 200
    assert demo_response.content == b"public-demo-preview"
    assert "public" in demo_response.headers["cache-control"]
    assert client.get(f"/api/tiles/{private.id}/preview").status_code == 404
    foreign_response = client.get(
        f"/api/tiles/{private.id}/preview", headers=auth_header(other_token)
    )
    assert foreign_response.status_code == 404
    owner_response = client.get(
        f"/api/tiles/{private.id}/preview", headers=auth_header(owner_token)
    )
    assert owner_response.status_code == 200
    assert owner_response.content == b"private-preview"
    assert owner_response.headers["cache-control"] == "private, no-store"


def test_missing_preview_returns_404(client, database, login_token, monkeypatch, tmp_path):
    owner = add_user(database, "owner-no-preview@example.invalid", "ownernopreview", "test-owner-password")
    private = add_dataset(database, "missing-private-preview", owner=owner)
    token = login_token(owner.email, "test-owner-password")
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)

    response = client.get(
        f"/api/tiles/{private.id}/preview", headers=auth_header(token)
    )
    assert response.status_code == 404


def test_dataset_api_metadata_omits_storage_preview_url(
    client, database, login_token
):
    owner = add_user(database, "owner-metadata@example.invalid", "ownermetadata", "test-owner-password")
    private = add_dataset(database, "private-preview-url", owner=owner)
    private.extra_metadata = {
        "preview_url": "https://storage.invalid/private-preview.jpg",
        "r2_upload_error": "details include endpoint https://internal.invalid and secret-marker",
        "error": "internal stack detail",
        "internal_path": "C:/private/dataset.tif",
        "private_tiles_uploaded_to_cloud": True,
        "width": 2048,
        "bounds": {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1},
        "driver": "GTiff",
        "tiles_uploaded_to_cloud": True,
    }
    database.commit()
    token = login_token(owner.email, "test-owner-password")

    response = client.get(
        f"/api/datasets/{private.id}", headers=auth_header(token)
    )
    assert response.status_code == 200
    returned_metadata = response.json()["extra_metadata"]
    assert returned_metadata == {
        "width": 2048,
        "bounds": {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1},
        "driver": "GTiff",
    }
    assert "preview_url" not in response.text
    assert "secret-marker" not in response.text
    assert "original_file_path" not in response.json()
    assert "tile_base_path" not in response.json()


def test_dataset_search_and_comparison_follow_visibility(client, database, login_token):
    owner = add_user(database, "owner-search@example.invalid", "ownersearch", "test-owner-password")
    other = add_user(database, "other-search@example.invalid", "othersearch", "test-other-password")
    demo = add_dataset(database, "shared-search-demo", demo=True)
    own = add_dataset(database, "private-search-own", owner=owner)
    foreign = add_dataset(database, "private-search-foreign", owner=other)
    token = login_token(owner.email, "test-owner-password")
    headers = auth_header(token)

    response = client.get("/api/search/datasets?q=search", headers=headers)
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {demo.id, own.id}
    assert response.headers["cache-control"] == "private, no-store"
    anonymous_search = client.get("/api/search/datasets?q=search")
    assert anonymous_search.json()[0]["id"] == demo.id
    assert "cache-control" not in anonymous_search.headers

    allowed = client.post("/api/compare", headers=headers, json={"dataset_ids": [demo.id, own.id]})
    assert allowed.status_code == 200
    assert allowed.headers["cache-control"] == "private, no-store"
    assert client.get("/api/compare", params={"ids": f"{demo.id},{own.id}"}).status_code == 405
    denied = client.post("/api/compare", headers=headers, json={"dataset_ids": [demo.id, foreign.id]})
    assert denied.status_code == 404
    duplicate = client.post("/api/compare", headers=headers, json={"dataset_ids": [demo.id, demo.id]})
    assert duplicate.status_code == 400


def test_private_cloud_preview_is_proxied_without_external_storage(
    client, database, login_token, monkeypatch
):
    class FakeStorageClient:
        def get_object(self, **_kwargs):
            return {"Body": [b"mock-private-preview"], "ContentType": "image/jpeg"}

    owner = add_user(database, "owner-cloud-preview@example.invalid", "ownercloudpreview", "test-owner-password")
    private = add_dataset(database, "cloud-private-preview", owner=owner)
    token = login_token(owner.email, "test-owner-password")
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "_client", FakeStorageClient())
    monkeypatch.setattr(cloud_storage, "bucket_name", "public-test-bucket")
    monkeypatch.setattr(cloud_storage, "private_bucket_name", "private-test-bucket")
    monkeypatch.setattr(cloud_storage, "private_access_confirmed", True)

    response = client.get(
        f"/api/tiles/{private.id}/preview", headers=auth_header(token)
    )
    assert response.status_code == 200
    assert response.content == b"mock-private-preview"
    assert response.headers["cache-control"] == "private, no-store"


def test_private_tile_api_uses_private_bucket_only_after_owner_check(
    client, database, login_token, monkeypatch
):
    class FakeStorageClient:
        def __init__(self):
            self.buckets = []

        def get_object(self, *, Bucket, Key):
            self.buckets.append(Bucket)
            return {"Body": [b"mock-private-tile"], "ContentType": "image/png"}

    owner = add_user(database, "owner-cloud-tile@example.invalid", "ownercloudtile", "test-owner-password")
    other = add_user(database, "other-cloud-tile@example.invalid", "othercloudtile", "test-other-password")
    private = add_dataset(database, "cloud-private-tile", owner=owner)
    private.extra_metadata = {"private_tiles_uploaded_to_cloud": True}
    database.commit()
    fake_storage = FakeStorageClient()
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "bucket_name", "public-test-bucket")
    monkeypatch.setattr(cloud_storage, "private_bucket_name", "private-test-bucket")
    monkeypatch.setattr(cloud_storage, "private_access_confirmed", True)
    monkeypatch.setattr(cloud_storage, "_client", fake_storage)
    monkeypatch.setattr(tile_cache, "enabled", False)
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")

    denied = client.get(
        f"/api/tiles/{private.id}/0/0/0.png", headers=auth_header(other_token)
    )
    assert denied.status_code == 404
    assert fake_storage.buckets == []

    allowed = client.get(
        f"/api/tiles/{private.id}/0/0/0.png", headers=auth_header(owner_token)
    )
    assert allowed.status_code == 200
    assert allowed.content == b"mock-private-tile"
    assert allowed.headers["cache-control"] == "private, no-store"
    assert fake_storage.buckets == ["private-test-bucket"]


def test_legacy_private_assets_never_fall_back_to_public_bucket(
    client, database, login_token, monkeypatch, tmp_path
):
    class FakeStorageClient:
        def __init__(self):
            self.calls = []

        def get_object(self, **kwargs):
            self.calls.append(("get", kwargs.get("Bucket")))
            raise AssertionError("Legacy private route must not read cloud objects")

        def head_object(self, **kwargs):
            self.calls.append(("head", kwargs.get("Bucket")))
            raise AssertionError("Legacy private route must not inspect public objects")

    owner = add_user(database, "owner-legacy@example.invalid", "ownerlegacy", "test-legacy-password")
    dataset = add_dataset(database, "legacy-private-cloud", owner=owner)
    dataset.tile_base_path = str(tmp_path / "missing-legacy-tiles")
    dataset.extra_metadata = {
        "tiles_uploaded_to_cloud": True,
        "preview_url": "https://legacy.invalid/private-preview.jpg",
    }
    database.commit()
    token = login_token(owner.email, "test-legacy-password")
    fake_storage = FakeStorageClient()
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "bucket_name", "legacy-public-bucket")
    monkeypatch.setattr(cloud_storage, "private_bucket_name", "")
    monkeypatch.setattr(cloud_storage, "private_access_confirmed", False)
    monkeypatch.setattr(cloud_storage, "_client", fake_storage)
    monkeypatch.setattr(cloud_storage, "_initialized", True)
    monkeypatch.setattr(
        type(cloud_storage), "private_enabled", property(lambda _self: False)
    )
    monkeypatch.setattr(tile_cache, "enabled", False)

    tile_response = client.get(
        f"/api/tiles/{dataset.id}/0/0/0.png", headers=auth_header(token)
    )
    preview_response = client.get(
        f"/api/tiles/{dataset.id}/preview", headers=auth_header(token)
    )

    assert tile_response.status_code == 503
    assert preview_response.status_code == 503
    assert fake_storage.calls == []


def test_cloud_demo_preview_checks_existence_before_redirect(
    client, database, tmp_path, monkeypatch
):
    demo = add_dataset(database, "cloud-preview-demo", demo=True)
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "bucket_name", "public-demo-bucket")
    monkeypatch.setattr(cloud_storage, "public_url", "https://assets.invalid")
    checked = []
    monkeypatch.setattr(
        cloud_storage,
        "public_object_exists",
        lambda key: checked.append(key) or True,
    )

    response = client.get(
        f"/api/tiles/{demo.id}/preview", follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith(
        f"https://assets.invalid/previews/{demo.id}_preview.jpg?v="
    )
    assert checked == [f"previews/{demo.id}_preview.jpg"]


def test_cloud_demo_preview_missing_object_returns_404(
    client, database, tmp_path, monkeypatch
):
    demo = add_dataset(database, "missing-cloud-demo-preview", demo=True)
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "bucket_name", "public-demo-bucket")
    monkeypatch.setattr(cloud_storage, "public_url", "https://assets.invalid")
    monkeypatch.setattr(cloud_storage, "public_object_exists", lambda _key: False)

    response = client.get(f"/api/tiles/{demo.id}/preview")
    assert response.status_code == 404


def test_cloud_demo_preview_storage_error_returns_503(
    client, database, tmp_path, monkeypatch
):
    from app.services.storage import StorageUnavailableError

    demo = add_dataset(database, "cloud-error-demo-preview", demo=True)
    monkeypatch.setattr(settings, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(cloud_storage, "enabled", True)
    monkeypatch.setattr(cloud_storage, "bucket_name", "public-demo-bucket")
    monkeypatch.setattr(cloud_storage, "public_url", "https://assets.invalid")

    def storage_error(_key):
        raise StorageUnavailableError

    monkeypatch.setattr(cloud_storage, "public_object_exists", storage_error)
    response = client.get(f"/api/tiles/{demo.id}/preview")
    assert response.status_code == 503
