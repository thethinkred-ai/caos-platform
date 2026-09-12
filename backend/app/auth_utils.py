"""Shared helpers for issuing and revoking auth sessions.

Used by password login (auth.py) and both OAuth callbacks so that every
login path creates a server-side Session row — without it /auth/refresh
rejects the refresh token.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Session as SessionModel
from .security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_cookie_settings,
    get_refresh_cookie_settings,
)

logger = logging.getLogger(__name__)


def issue_session(response: Response, user_id: int, db: Session) -> None:
    """Create a Session row and set access/refresh cookies on any response."""
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    _, jti = decode_refresh_token(refresh)
    settings = get_settings()
    db.add(SessionModel(
        user_id=user_id,
        jti=jti,
        refresh_token_hash=hashlib.sha256(refresh.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    ))
    db.flush()
    response.set_cookie(value=access, **get_cookie_settings())
    response.set_cookie(value=refresh, **get_refresh_cookie_settings())


def revoke_sessions(db: Session, user_id: int, keep_jti: str | None = None) -> None:
    """Revoke all sessions of a user, optionally keeping the current one."""
    stmt = (
        update(SessionModel)
        .where(SessionModel.user_id == user_id, SessionModel.revoked.is_(False))
        .values(revoked=True)
    )
    if keep_jti is not None:
        stmt = stmt.where(SessionModel.jti != keep_jti)
    db.execute(stmt)
