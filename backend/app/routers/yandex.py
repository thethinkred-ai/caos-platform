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

YANDEX_OAUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_INFO_URL = "https://login.yandex.ru/info"

STATE_COOKIE = "caos_yandex_state"


@router.get("/auth/yandex")
def yandex_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.yandex_client_id:
        raise HTTPException(status_code=503, detail="Yandex OAuth not configured. Set YANDEX_CLIENT_ID in .env")
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.yandex_redirect_uri,
        "state": state,
    })
    response = RedirectResponse(url=f"{YANDEX_OAUTH_URL}?{params}")
    response.set_cookie(STATE_COOKIE, state, httponly=True, secure="https" in settings.frontend_url,
                        samesite="lax", path="/", max_age=300)
    return response


@router.get("/auth/yandex/callback")
def yandex_callback(code: str | None = None, state: str | None = None, request: Request = None, db: Db = None) -> RedirectResponse:
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
            "client_id": settings.yandex_client_id,
            "client_secret": settings.yandex_client_secret,
        }
        token_resp = httpx.post(YANDEX_TOKEN_URL, data=token_data, timeout=15)
        logger.info("Yandex token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
            # Never log the response body: on errors it can echo the secret.
            logger.error("Yandex token exchange failed: HTTP %s", token_resp.status_code)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = httpx.get(
            YANDEX_INFO_URL,
            params={"format": "json"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        logger.info("Yandex user API status: %s", user_resp.status_code)
        if user_resp.status_code != 200:
            logger.error("Yandex user API failed: HTTP %s", user_resp.status_code)
        user_resp.raise_for_status()
        yandex_user = user_resp.json()

        yandex_id = str(yandex_user["id"])
        email = yandex_user.get("default_email") or ""
        if not email:
            emails = yandex_user.get("emails") or []
            email = emails[0] if emails else ""
        # Yandex verifies the mailbox it returns as default_email, so a present
        # address may be trusted as confirmed.
        email_verified = bool(yandex_user.get("default_email"))
        display_name = (
            yandex_user.get("real_name")
            or yandex_user.get("display_name")
            or yandex_user.get("login")
            or "Yandex User"
        )

        if not email:
            return RedirectResponse(url=f"{frontend_url}/?error=email_required")

        identity = db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider == "yandex", AuthIdentity.provider_subject == yandex_id)
        )
        if identity:
            user = identity.user
            user.display_name = display_name
        else:
            user = db.scalar(select(User).where(User.email == email))
            if not email_verified:
                return RedirectResponse(url=f"{frontend_url}/?error=email_not_verified")
            if user:
                db.add(AuthIdentity(provider="yandex", provider_subject=yandex_id, user_id=user.id, verified_email=True))
            else:
                user = User(email=email, password_hash=None, stepik_id=None, is_verified=True)
                user.profile = UserProfile(display_name=display_name, bio="")
                db.add(user)
                db.flush()
                db.add(AuthIdentity(provider="yandex", provider_subject=yandex_id, user_id=user.id, verified_email=True))

        db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="yandex_login", detail=""))
        response = RedirectResponse(url=f"{frontend_url}/auth/callback")
        issue_session(response, user.id, db)
        db.commit()
        response.delete_cookie(STATE_COOKIE, path="/")
        return response
    except Exception as e:
        logger.exception("Yandex OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")
