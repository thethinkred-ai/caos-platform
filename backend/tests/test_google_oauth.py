"""Google OAuth callback tests (httpx mocked; no network)."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers.google import STATE_COOKIE
from tests.conftest import TestingSessionLocal, register_and_login


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"fake HTTP {self.status_code}")

    def json(self):
        return self._payload


def _mock_google(monkeypatch, *, email, google_id="g-123", verified=True):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(200, {"access_token": "google-access-token"})

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(200, {
            "id": google_id,
            "email": email,
            "verified_email": verified,
            "name": "Google User",
        })

    monkeypatch.setattr("app.routers.google.httpx.post", fake_post)
    monkeypatch.setattr("app.routers.google.httpx.get", fake_get)


def _callback(client):
    client.cookies.set(STATE_COOKIE, "state-ok")
    return client.get(
        "/api/v1/auth/google/callback",
        params={"code": "abc", "state": "state-ok"},
        follow_redirects=False,
    )


def test_google_login_creates_session_row(client, outbox, monkeypatch):
    # Regression: OAuth used to set refresh cookies without a Session row,
    # so /auth/refresh always rejected the token.
    _mock_google(monkeypatch, email="guser@example.com")
    response = _callback(client)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/auth/callback")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "guser@example.com"
    assert client.post("/api/v1/auth/refresh").status_code == 200


def test_google_unverified_email_cannot_take_over_account(client, outbox, monkeypatch):
    # Regression: an unverified Google email used to log in as an existing
    # local account with the same email.
    victim = TestClient(app)
    register_and_login(victim, outbox, email="victim@example.com")

    _mock_google(monkeypatch, email="victim@example.com", google_id="g-attacker", verified=False)
    response = _callback(client)
    assert response.status_code == 307
    assert "error=email_not_verified" in response.headers["location"]

    # No session was issued for the attacker.
    assert client.get("/api/v1/auth/me").status_code == 401

    from sqlalchemy import select

    from app.models import AuthIdentity

    db = TestingSessionLocal()
    assert db.scalar(select(AuthIdentity).where(AuthIdentity.provider_subject == "g-attacker")) is None
    db.close()

    # The victim's password still works.
    again = TestClient(app)
    assert again.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "strong-password-123"},
    ).status_code == 200


def test_google_unverified_email_creates_no_account(client, monkeypatch):
    from sqlalchemy import func, select

    from app.models import User

    _mock_google(monkeypatch, email="ghost@example.com", google_id="g-ghost", verified=False)
    response = _callback(client)
    assert "error=email_not_verified" in response.headers["location"]

    db = TestingSessionLocal()
    count = db.scalar(select(func.count()).select_from(User).where(User.email == "ghost@example.com"))
    db.close()
    assert count == 0


def test_google_verified_email_links_existing_account(client, outbox, monkeypatch):
    user = register_and_login(client, outbox, email="linkme@example.com")
    _mock_google(monkeypatch, email="linkme@example.com", google_id="g-link")
    response = _callback(client)
    assert response.status_code == 307

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]
