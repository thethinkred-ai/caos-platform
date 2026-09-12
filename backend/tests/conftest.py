"""Shared test fixtures.

The test database is an in-memory SQLite engine wired via dependency
override, dropped and recreated for every test. Raw email tokens are
captured through an outbox because only their hashes reach the database.
"""

import os

# Must be set before app modules import config/db. The global engine is
# only touched by create_all at import time; tests use the in-memory
# engine below via dependency override.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET", "test-only-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from app.routers.auth import limiter

    if hasattr(limiter, "reset"):
        limiter.reset()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def outbox(monkeypatch):
    """Capture raw tokens from make_email_token: DB stores only hashes."""
    captured: dict[str, list[str]] = {}
    from app.routers import auth as auth_module

    original = auth_module.make_email_token

    def record(purpose: str, ttl):
        raw, token_hash = original(purpose, ttl)
        captured.setdefault(purpose, []).append(raw)
        return raw, token_hash

    monkeypatch.setattr(auth_module, "make_email_token", record)
    return captured


def register_and_login(
    client: TestClient,
    outbox: dict,
    email: str = "user@example.com",
    password: str = "strong-password-123",
    display_name: str = "Tester",
) -> dict:
    """Register, verify the email and log in; returns the login payload."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    token = outbox["verify"][-1]
    response = client.get("/api/v1/auth/verify", params={"token": token})
    assert response.status_code == 200, response.text
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["user"]
