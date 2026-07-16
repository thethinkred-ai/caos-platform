import logging
import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User
from ..security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()
Db = Annotated[Session, Depends(get_db)]

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API_URL = "https://www.googleapis.com/oauth2/v2"


@router.get("/auth/google")
def google_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env")
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    })
    return RedirectResponse(url=f"{GOOGLE_OAUTH_URL}?{params}")


@router.get("/auth/google/callback")
def google_callback(code: str | None = None, db: Db = None) -> RedirectResponse:
    settings = get_settings()
    frontend_url = settings.frontend_url

    if not code:
        return RedirectResponse(url=f"{frontend_url}/?error=missing_code")

    try:
        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.google_redirect_uri,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
            },
            timeout=15,
        )
        logger.info("Google token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
            logger.error("Google token error: %s", token_resp.text)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = httpx.get(
            f"{GOOGLE_API_URL}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        logger.info("Google user API status: %s", user_resp.status_code)
        if user_resp.status_code != 200:
            logger.error("Google user API error: %s", user_resp.text)
        user_resp.raise_for_status()
        google_user = user_resp.json()

        google_id = google_user["id"]
        email = google_user.get("email", "")
        display_name = google_user.get("name", "") or google_user.get("email", "Google User")

        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                password_hash=None,
                display_name=display_name,
                stepik_id=None,
            )
            db.add(user)
        else:
            user.display_name = display_name

        db.commit()
        db.refresh(user)

        token = create_access_token(user.id)
        return RedirectResponse(url=f"{frontend_url}/?token={token}")
    except Exception as e:
        logger.exception("Google OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")
