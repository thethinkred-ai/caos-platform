"""Local development helpers: registration without SMTP must not strand
the account behind an email that never arrives (external feedback,
13.11.2026), and /me/export must return JSON, not a datetime 500."""

import logging

import pytest

from app.config import Settings, get_settings
from tests.conftest import register_and_login


def test_export_returns_json(client, outbox):
    """Regression: /me/export built JSONResponse from model_dump() without
    mode="json" — datetime fields crashed it with a 500."""
    register_and_login(client, outbox, email="export@example.com")
    token = client.cookies.get("caos_token")
    response = client.get("/api/v1/auth/me/export", cookies={"caos_token": token})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "export@example.com"
    assert isinstance(body["user"]["created_at"], str)


def test_auto_verify_email_allows_immediate_login(client, outbox, monkeypatch):
    """AUTO_VERIFY_EMAIL=true: register -> login 200 without any email."""
    monkeypatch.setattr(get_settings(), "auto_verify_email", True)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "local@example.com", "password": "strong-password-123", "display_name": "Local"},
    )
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "local@example.com", "password": "strong-password-123"},
    )
    assert login.status_code == 200, login.text
    assert "verify" not in outbox  # no verification email in this mode


def test_auto_verify_rescues_stranded_unverified_account(client, outbox, monkeypatch):
    """An account registered before the flag must become usable after it
    is set: re-registering the same email verifies it."""
    monkeypatch.setattr(get_settings(), "auto_verify_email", False)
    client.post(
        "/api/v1/auth/register",
        json={"email": "stranded@example.com", "password": "strong-password-123", "display_name": "Stranded"},
    )
    monkeypatch.setattr(get_settings(), "auto_verify_email", True)
    client.post(
        "/api/v1/auth/register",
        json={"email": "stranded@example.com", "password": "strong-password-123", "display_name": "Stranded"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "stranded@example.com", "password": "strong-password-123"},
    )
    assert login.status_code == 200, login.text


def test_unsent_emails_logged_with_verification_link(client, outbox, monkeypatch, caplog):
    """LOG_UNSENT_EMAILS=true: the skipped email lands in the log together
    with the verification link, so a local setup without SMTP still works."""
    settings = get_settings()
    monkeypatch.setattr(settings, "log_unsent_emails", True)
    monkeypatch.setattr(settings, "smtp_host", "")
    with caplog.at_level(logging.WARNING, logger="app.email"):
        client.post(
            "/api/v1/auth/register",
            json={"email": "nologs@example.com", "password": "strong-password-123", "display_name": "NoSMTP"},
        )
    assert outbox["verify"], "token was generated"
    link = f"/auth/verify?token={outbox['verify'][-1]}"
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "EMAIL NOT SENT" in joined
    assert link in joined


def test_auto_verify_refused_on_production_database():
    """The dev flag must never silence email verification on a real DB."""
    settings = Settings(
        database_url="postgresql+psycopg://caos:real-password@db:5432/caos",
        jwt_secret="a-real-secret-not-the-default-value",
        auto_verify_email=True,
    )
    with pytest.raises(RuntimeError, match="AUTO_VERIFY_EMAIL"):
        settings.validate_production()
