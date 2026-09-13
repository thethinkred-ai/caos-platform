import logging
import secrets
import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth_utils import issue_session
from ..config import get_settings
from ..db import get_db
from ..models import AuthIdentity, AuditEvent, User, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter()
Db = Annotated[Session, Depends(get_db)]

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API_URL = "https://www.googleapis.com/oauth2/v2"

STATE_COOKIE = "caos_oauth_state"


@router.get("/auth/google")
def google_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env")
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    })
    response = RedirectResponse(url=f"{GOOGLE_OAUTH_URL}?{params}")
    response.set_cookie(STATE_COOKIE, state, httponly=True, secure="https" in settings.frontend_url, samesite="lax", path="/", max_age=300)
    return response


@router.get("/auth/google/callback")
def google_callback(code: str | None = None, state: str | None = None, request: Request = None, db: Db = None) -> RedirectResponse:
    settings = get_settings()
    frontend_url = settings.frontend_url

    if not code:
        return RedirectResponse(url=f"{frontend_url}/?error=missing_code")

    expected_state = request.cookies.get(STATE_COOKIE) if request else None
    if not state or not expected_state or state != expected_state:
        return RedirectResponse(url=f"{frontend_url}/?error=state_mismatch")

    try:
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.google_redirect_uri,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
        }
        token_resp = httpx.post(GOOGLE_TOKEN_URL, data=token_data, timeout=15)
        logger.info("Google token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
            # Never log the response body: on errors it can echo the secret.
            logger.error("Google token exchange failed: HTTP %s", token_resp.status_code)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = httpx.get(
            f"{GOOGLE_API_URL}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        logger.info("Google user API status: %s", user_resp.status_code)
        if user_resp.status_code != 200:
            logger.error("Google user API failed: HTTP %s", user_resp.status_code)
        user_resp.raise_for_status()
        google_user = user_resp.json()

        google_id = google_user["id"]
        email = google_user.get("email", "")
        email_verified = google_user.get("verified_email", False)
        display_name = google_user.get("name", "") or google_user.get("email", "Google User")

        identity = db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider == "google", AuthIdentity.provider_subject == google_id)
        )
        if identity:
            user = identity.user
            user.display_name = display_name
        else:
            user = db.scalar(select(User).where(User.email == email))
            if not email_verified:
                # An unverified Google email must never grant access to an
                # existing local account nor create a login-able one.
                return RedirectResponse(url=f"{frontend_url}/?error=email_not_verified")
            if user:
                db.add(AuthIdentity(provider="google", provider_subject=google_id, user_id=user.id, verified_email=True))
            else:
                user = User(
                    email=email,
                    password_hash=None,
                    stepik_id=None,
                    is_verified=True,
                )
                user.profile = UserProfile(display_name=display_name, bio="")
                db.add(user)
                db.flush()
                db.add(AuthIdentity(provider="google", provider_subject=google_id, user_id=user.id, verified_email=True))

        db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="google_login", detail=""))
        response = RedirectResponse(url=f"{frontend_url}/auth/callback")
        issue_session(response, user.id, db)
        db.commit()
        response.delete_cookie(STATE_COOKIE, path="/")
        return response
    except Exception as e:
        logger.exception("Google OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")
