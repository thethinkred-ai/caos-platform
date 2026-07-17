import hashlib
import logging
import secrets
import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import AuthIdentity, AuditEvent, User
from ..security import create_access_token, create_refresh_token, get_cookie_settings, get_refresh_cookie_settings

logger = logging.getLogger(__name__)
router = APIRouter()
Db = Annotated[Session, Depends(get_db)]

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API_URL = "https://www.googleapis.com/oauth2/v2"

STATE_COOKIE = "caos_oauth_state"
PKCE_VERIFIER_COOKIE = "caos_oauth_pkce"


@router.get("/auth/google")
def google_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = hashlib.sha256(verifier.encode()).digest().hex()
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    response = RedirectResponse(url=f"{GOOGLE_OAUTH_URL}?{params}")
    response.set_cookie(STATE_COOKIE, state, httponly=True, secure="https" in settings.frontend_url, samesite="lax", path="/", max_age=300)
    response.set_cookie(PKCE_VERIFIER_COOKIE, verifier, httponly=True, secure="https" in settings.frontend_url, samesite="lax", path="/", max_age=300)
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

    pkce_verifier = request.cookies.get(PKCE_VERIFIER_COOKIE) if request else None

    try:
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.google_redirect_uri,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
        }
        if pkce_verifier:
            token_data["code_verifier"] = pkce_verifier
        token_resp = httpx.post(GOOGLE_TOKEN_URL, data=token_data, timeout=15)
        logger.info("Google token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
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
            if user:
                if email_verified:
                    db.add(AuthIdentity(provider="google", provider_subject=google_id, user_id=user.id, verified_email=True))
            else:
                user = User(
                    email=email,
                    password_hash=None,
                    display_name=display_name,
                    stepik_id=None,
                    is_verified=email_verified,
                )
                db.add(user)
                db.flush()
                if email_verified:
                    db.add(AuthIdentity(provider="google", provider_subject=google_id, user_id=user.id, verified_email=True))

        db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="google_login", detail=""))
        db.commit()
        db.refresh(user)

        access_jwt = create_access_token(user.id)
        refresh_jwt = create_refresh_token(user.id)
        response = RedirectResponse(url=f"{frontend_url}/auth/callback")
        response.set_cookie(value=access_jwt, **get_cookie_settings())
        response.set_cookie(value=refresh_jwt, **get_refresh_cookie_settings())
        response.delete_cookie(STATE_COOKIE, path="/")
        response.delete_cookie(PKCE_VERIFIER_COOKIE, path="/")
        return response
    except Exception as e:
        logger.exception("Google OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")
