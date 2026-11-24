"""Isolated test configuration; never points at an operator database."""

import os
import sys
from pathlib import Path
from tempfile import gettempdir

TEST_ROOT = Path(gettempdir()) / "philos-admin-security-tests"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///" + str(
    TEST_ROOT / "configuration-only.db"
).replace("\\", "/")
os.environ["SECRET_KEY"] = "test-only-random-value-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
os.environ["USE_S3"] = "False"
os.environ["AWS_ACCESS_KEY_ID"] = ""
os.environ["AWS_SECRET_ACCESS_KEY"] = ""
os.environ["AWS_BUCKET_NAME"] = ""
os.environ["S3_ENDPOINT_URL"] = ""
os.environ["R2_PUBLIC_URL"] = ""
os.environ["PRIVATE_S3_BUCKET_NAME"] = ""
os.environ["PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED"] = "False"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["TILES_DIR"] = str(TEST_ROOT / "tiles")
os.environ["DATASETS_DIR"] = str(TEST_ROOT / "datasets")
os.environ["TEMP_DIR"] = str(TEST_ROOT / "temp")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.middleware.cache import CacheMiddleware, response_cache
from app.routers import admin, annotations_simple, auth, datasets, search, tiles


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(database):
    response_cache.clear()
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth")
    app.include_router(admin.router, prefix="/api")
    app.include_router(datasets.router, prefix="/api")
    app.include_router(tiles.router, prefix="/api")
    app.include_router(datasets.preview_router)
    app.include_router(annotations_simple.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.add_middleware(CacheMiddleware)

    def override_get_db():
        yield database

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    response_cache.clear()


@pytest.fixture
def login_token(client):
    def login(email, password):
        response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    return login
