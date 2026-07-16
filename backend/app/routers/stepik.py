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
from ..deps import current_user
from ..models import User
from ..security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

STEPIK_OAUTH_URL = "https://stepik.org/oauth2"
STEPIK_API_URL = "https://stepik.org/api"

COURSE_INFO = {
    288738: {"title": "Наука логики Гегеля", "slug": "hegel"},
    288774: {"title": "Капитал Маркса", "slug": "capital"},
    285340: {"title": "Ленин «Карл Маркс»", "slug": "lenin"},
}


@router.get("/auth/stepik")
def stepik_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.stepik_client_id:
        raise HTTPException(status_code=503, detail="Stepik OAuth not configured. Set STEPIK_CLIENT_ID in .env")
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.stepik_client_id,
        "redirect_uri": settings.stepik_redirect_uri,
        "scope": "read write",
    })
    return RedirectResponse(url=f"{STEPIK_OAUTH_URL}/authorize/?{params}")


@router.get("/auth/stepik/callback")
def stepik_callback(code: str | None = None, db: Db = None) -> RedirectResponse:
    settings = get_settings()
    frontend_url = settings.frontend_url

    if not code:
        return RedirectResponse(url=f"{frontend_url}/?error=missing_code")

    try:
        token_resp = httpx.post(
            f"{STEPIK_OAUTH_URL}/token/",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.stepik_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(settings.stepik_client_id, settings.stepik_client_secret),
            timeout=15,
        )
        logger.info("Stepik token exchange status: %s", token_resp.status_code)
        if token_resp.status_code != 200:
            logger.error("Stepik token error: %s", token_resp.text)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = httpx.get(
            f"{STEPIK_API_URL}/stepics/1",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        logger.info("Stepik user API status: %s", user_resp.status_code)
        if user_resp.status_code != 200:
            logger.error("Stepik user API error: %s", user_resp.text)
        user_resp.raise_for_status()
        stepik_user = user_resp.json()["users"][0]

        stepik_id = stepik_user["id"]
        email = stepik_user.get("email") or f"stepik_{stepik_id}@stepik.org"
        first_name = stepik_user.get("first_name", "")
        last_name = stepik_user.get("last_name", "")
        display_name = f"{first_name} {last_name}".strip() or f"Stepik #{stepik_id}"

        user = db.scalar(select(User).where(User.stepik_id == stepik_id))
        if not user:
            user = db.scalar(select(User).where(User.email == email))
            if user:
                user.stepik_id = stepik_id
            else:
                user = User(
                    email=email,
                    password_hash=None,
                    display_name=display_name,
                    stepik_id=stepik_id,
                )
                db.add(user)
        else:
            user.display_name = display_name

        db.commit()
        db.refresh(user)

        token = create_access_token(user.id)
        return RedirectResponse(url=f"{frontend_url}/?token={token}")
    except Exception as e:
        logger.exception("Stepik OAuth failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/?error=auth_failed")


@router.get("/auth/stepik/courses")
def get_stepik_courses(user: CurrentUser) -> dict:
    if not user.stepik_id:
        return {"courses": []}

    settings = get_settings()
    course_ids = settings.stepik_course_id_list
    result = []

    for cid in course_ids:
        info = COURSE_INFO.get(cid, {"title": f"Course {cid}", "slug": str(cid)})
        try:
            resp = httpx.get(
                f"{STEPIK_API_URL}/courses/{cid}",
                timeout=10,
            )
            course_data = resp.json().get("courses", [{}])[0] if resp.status_code == 200 else {}
            result.append({
                "id": cid,
                "title": info["title"],
                "slug": info["slug"],
                "url": f"https://stepik.org/course/{cid}",
                "learners_count": course_data.get("learners_count", 0),
                "sections_count": course_data.get("sections_count", 0),
            })
        except Exception:
            result.append({
                "id": cid,
                "title": info["title"],
                "slug": info["slug"],
                "url": f"https://stepik.org/course/{cid}",
                "learners_count": 0,
                "sections_count": 0,
            })

    return {"courses": result}
