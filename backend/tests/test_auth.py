"""Auth flow tests: registration, verification, sessions, password reset."""

from tests.conftest import register_and_login


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_returns_generic_message_without_token(client, outbox):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "strong-password-123", "display_name": "New"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" not in body
    assert body["message"] == "Account created. Check your email for a verification link."
    assert outbox["verify"]


def test_register_duplicate_returns_identical_response(client, outbox):
    payload = {"email": "dup@example.com", "password": "strong-password-123", "display_name": "Dup"}
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()


def test_login_before_verification_rejected(client, outbox):
    client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@example.com", "password": "strong-password-123", "display_name": "Unverified"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@example.com", "password": "strong-password-123"},
    )
    assert response.status_code == 403


def test_verify_invalid_token_rejected(client):
    response = client.get("/api/v1/auth/verify", params={"token": "verify:9999999999:not-a-real-token"})
    assert response.status_code == 400


def test_verify_token_cannot_reset_password(client, outbox):
    client.post(
        "/api/v1/auth/register",
        json={"email": "victim@example.com", "password": "strong-password-123", "display_name": "Victim"},
    )
    verify_token = outbox["verify"][-1]
    response = client.post(
        "/api/v1/auth/reset-password/confirm",
        json={"token": verify_token, "new_password": "attacker-password-123"},
    )
    assert response.status_code == 400
    # Original password still works after verification.
    client.get("/api/v1/auth/verify", params={"token": verify_token})
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "strong-password-123"},
    )
    assert response.status_code == 200


def test_password_login_for_oauth_only_account_is_401_not_500(client):
    # OAuth accounts have password_hash=None — verify_password must not crash.
    from tests.conftest import TestingSessionLocal
    from app.models import User, UserProfile

    db = TestingSessionLocal()
    oauth_user = User(email="google-only@example.com", password_hash=None, is_verified=True)
    oauth_user.profile = UserProfile(display_name="G", bio="")
    db.add(oauth_user)
    db.commit()
    db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "google-only@example.com", "password": "whatever-password-123"},
    )
    assert response.status_code == 401


def test_full_register_verify_login_flow(client, outbox):
    user = register_and_login(client, outbox)
    assert user["email"] == "user@example.com"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


def test_refresh_rotates_session(client, outbox):
    register_and_login(client, outbox)
    old_refresh = client.cookies.get("caos_refresh")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    # The rotated-out refresh token must no longer work.
    client.cookies.set("caos_refresh", old_refresh)
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_revokes_session(client, outbox):
    register_and_login(client, outbox)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_change_password_revokes_other_sessions(client, outbox):
    from fastapi.testclient import TestClient

    from app.main import app

    register_and_login(client, outbox, email="shared@example.com")
    other_device = TestClient(app)
    response = other_device.post(
        "/api/v1/auth/login",
        json={"email": "shared@example.com", "password": "strong-password-123"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "strong-password-123", "new_password": "new-strong-password-456"},
    )
    assert response.status_code == 200

    # The device that changed the password survives; the other one is revoked.
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert other_device.post("/api/v1/auth/refresh").status_code == 401


def test_reset_password_flow(client, outbox):
    register_and_login(client, outbox, email="reset@example.com")

    response = client.post("/api/v1/auth/reset-password", json={"email": "reset@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "If this email is registered, a reset link has been sent."

    reset_token = outbox["reset"][-1]
    response = client.post(
        "/api/v1/auth/reset-password/confirm",
        json={"token": reset_token, "new_password": "reset-password-789"},
    )
    assert response.status_code == 200

    # All pre-reset sessions are revoked.
    assert client.post("/api/v1/auth/refresh").status_code == 401
    # New password works, old one does not.
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "reset-password-789"},
    )
    assert response.status_code == 200
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "strong-password-123"},
    )
    assert response.status_code == 401


def test_sessions_listing_and_revoke(client, outbox):
    register_and_login(client, outbox)
    sessions = client.get("/api/v1/auth/sessions")
    assert sessions.status_code == 200
    body = sessions.json()
    assert len(body) >= 1
    response = client.post(f"/api/v1/auth/sessions/{body[0]['id']}/revoke")
    assert response.status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_user_out_exposes_privacy_settings(client, outbox):
    user = register_and_login(client, outbox, email="privacy@example.com")
    me = client.get("/api/v1/auth/me").json()
    assert me["profile_visibility"] == "private"
    assert me["ai_consent"] is False

    client.patch("/api/v1/profile/visibility", params={"visibility": "members"})
    client.patch("/api/v1/profile/ai-consent", params={"consent": "true"})
    me = client.get("/api/v1/auth/me").json()
    assert me["profile_visibility"] == "members"
    assert me["ai_consent"] is True
