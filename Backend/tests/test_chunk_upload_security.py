from datetime import datetime, timedelta

from app.config import settings
from app.models import User
from app.routers import datasets
from app.services.auth import get_password_hash


def add_user(db, email, username, password):
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def start_upload(client, token, *, filename="sample.tif", filesize=4, chunks=1):
    return client.post(
        "/api/datasets/upload/init",
        params={"filename": filename, "filesize": filesize, "total_chunks": chunks},
        headers=auth_header(token),
    )


def test_anonymous_cannot_initialize_chunk_upload(client):
    response = client.post(
        "/api/datasets/upload/init",
        params={"filename": "sample.tif", "filesize": 4, "total_chunks": 1},
    )
    assert response.status_code in {401, 403}


def test_owner_can_upload_chunk_and_foreign_user_cannot_append_or_cancel(
    client, database, login_token, monkeypatch, tmp_path
):
    owner = add_user(database, "chunk-owner@example.invalid", "chunkowner", "test-owner-password")
    other = add_user(database, "chunk-other@example.invalid", "chunkother", "test-other-password")
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")
    monkeypatch.setattr(settings, "TEMP_DIR", tmp_path)

    started = start_upload(client, owner_token)
    assert started.status_code == 200
    upload_id = started.json()["upload_id"]
    form = {"upload_id": upload_id, "chunk_index": "0"}
    files = {"chunk": ("part.bin", b"data", "application/octet-stream")}

    assert client.post(
        "/api/datasets/upload/chunk",
        data=form,
        files=files,
        headers=auth_header(other_token),
    ).status_code == 404
    assert client.delete(
        f"/api/datasets/upload/{upload_id}", headers=auth_header(other_token)
    ).status_code == 404
    assert client.post(
        "/api/datasets/upload/chunk",
        data=form,
        files=files,
        headers=auth_header(owner_token),
    ).status_code == 200


def test_chunk_index_and_filename_are_validated(client, database, login_token, monkeypatch, tmp_path):
    user = add_user(database, "chunk-validation@example.invalid", "chunkvalidation", "test-upload-password")
    token = login_token(user.email, "test-upload-password")
    monkeypatch.setattr(settings, "TEMP_DIR", tmp_path)
    started = start_upload(client, token)
    upload_id = started.json()["upload_id"]
    form = {"upload_id": upload_id, "chunk_index": "1"}
    files = {"chunk": ("part.bin", b"data", "application/octet-stream")}

    assert client.post(
        "/api/datasets/upload/chunk", data=form, files=files, headers=auth_header(token)
    ).status_code == 400
    assert start_upload(client, token, filename="../escape.tif").status_code == 400


def test_oversized_chunk_upload_is_rejected(client, database, login_token):
    user = add_user(database, "chunk-size@example.invalid", "chunksize", "test-size-password")
    token = login_token(user.email, "test-size-password")
    response = start_upload(
        client,
        token,
        filesize=settings.MAX_UPLOAD_SIZE + 1,
        chunks=(settings.MAX_UPLOAD_SIZE // datasets.UPLOAD_CHUNK_SIZE) + 1,
    )
    assert response.status_code == 413


def test_expired_upload_session_is_removed_safely(client, database, login_token, monkeypatch, tmp_path):
    user = add_user(database, "chunk-expired@example.invalid", "chunkexpired", "test-expiry-password")
    token = login_token(user.email, "test-expiry-password")
    monkeypatch.setattr(settings, "TEMP_DIR", tmp_path)
    started = start_upload(client, token)
    upload_id = started.json()["upload_id"]
    session = datasets.chunked_uploads[upload_id]
    session["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
    session_dir = session["temp_dir"]
    session_dir.mkdir(parents=True, exist_ok=True)

    response = client.delete(
        f"/api/datasets/upload/{upload_id}", headers=auth_header(token)
    )
    assert response.status_code == 410
    assert upload_id not in datasets.chunked_uploads
    assert not session_dir.exists()
