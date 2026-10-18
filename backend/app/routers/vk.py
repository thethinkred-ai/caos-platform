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

VK_OAUTH_URL = "https://oauth.vk.com/authorize"
VK_TOKEN_URL = "https://oauth.vk.com/access_token"
VK_API_URL = "https://api.vk.com/method"
VK_VERSION = "5.131"

STATE_COOKIE = "caos_vk_state"


@router.get("/auth/vk")
def vk_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.vk_client_id:
        raise HTTPException(status_code=503, detail="VK OAuth not configured. Set VK_CLIENT_ID in .env")
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode({
        "client_id": settings.vk_client_id,
        "redirect_uri": settings.vk_redirect_uri,
        "response_type": "code",
        "scope": "email",
        "state": state,
        "v": VK_VERSION,
    })
    response = RedirectResponse(url=f"{VK_OAUTH_URL}?{params}")
    response.set_cookie(STATE_COOKIE, state, httponly=True, secure="https" in settings.frontend_url,
                        samesite="lax", path="/", max_age=300)
    return response


@router.get("/auth/vk/callback")
def vk_callback(code: str | None = None, state: str | None = None, request: Request = None, db: Db = None) -> RedirectResponse:
    settings = get_settings()
    frontend_url = settings.frontend_url

    if not code:
        return RedirectResponse(url=f"{frontend_url}/?error=missing_code")

    expected_state = request.cookies.get(STATE_COOKIE) if request else None
    if not state or not expected_state or state != expected_state:
        return RedirectResponse(url=f"{frontend_url}/?error=state_mismatch")

    try:
        token_resp = httpx.get(
            VK_TOKEN_URL,
            params={
                "client_id": settings.vk_client_id,
                "client_secret": settings.vk_client_secret,
                "redirect_uri": settings.vk_redirect_uri,
                "code": code,
                "v": VK_VERSION,
            },
            timeout=15,
        )
        logger.info("VK token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
            logger.error("VK token exchange failed: HTTP %s", token_resp.status_code)
        token_resp.raise_for_status()
        token_json = token_resp.json()
        if "error" in token_json:
            logger.error("VK token exchange error: %s", token_json.get("error"))
            raise RuntimeError("vk_token_error")
        access_token = token_json["access_token"]
        vk_id = str(token_json["user_id"])
        email = (token_json.get("email") or "").strip()

        profile_resp = httpx.get(
            f"{VK_API_URL}/users.get",
            params={"user_ids": vk_id, "fields": "screen_name", "access_token": access_token, "v": VK_VERSION},
            timeout=15,
        )
        display_name = "VK User"
        try:
            items = profile_resp.json().get("response") or []
            if items:
                display_name = " ".join(p for p in (items[0].get("first_name"), items[0].get("last_name")) if p) or display_name
        except Exception:  # profile is cosmetic — never block login on it
            logger.warning("VK profile fetch failed", exc_info=True)

        # VK returns an email only when the app holds the "email" permission.
        # Without it the account still works: the identity is the VK id, and the
        # generated address is never used for mail (OAuth accounts have no password).
        if not email:
            email = f"vk{vk_id}@id.vk.caos.thinkred.ru"

        identity = db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider == "vk", AuthIdentity.provider_subject == vk_id)
        )
        if identity:
            user = identity.user
            user.display_name = display_name
        else:
            user = db.scalar(select(User).where(User.email == email))
            if user:
                db.add(AuthIdentity(provider="vk", provider_subject=vk_id, user_id=user.id, verified_email=bool(token_json.get("email"))))
            else:
                user = User(email=email, password_hash=None, stepik_id=None, is_verified=True)
                user.profile = UserProfile(display_name=display_name, bio="")
                db.add(user)
                db.flush()
                db.add(AuthIdentity(provider="vk", provider_subject=vk_id, user_id=user.id, verified_email=bool(token_json.get("email"))))

        db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="vk_login", detail=""))
        response = RedirectResponse(url=f"{frontend_url}/auth/callback")
        issue_session(response, user.id, db)
        db.commit()
        response.delete_cookie(STATE_COOKIE, path="/")
        return response
    except Exception as e:
        logger.exception("VK OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")
