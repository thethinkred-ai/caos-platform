import hashlib
import secrets as _secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Session as SessionModel, User
from ..schemas import (
    ChangePasswordRequest, ProfileUpdate, RefreshOut, ResetPasswordConfirm,
    ResetPasswordRequest, TokenOut, UserCreate, UserLogin, UserOut,
)
from ..email import send_email
from ..security import (
    COOKIE_NAME, REFRESH_COOKIE_NAME, create_access_token, create_refresh_token,
    decode_refresh_token, get_cookie_settings, get_refresh_cookie_settings,
    hash_password, verify_password,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
Db = Annotated[Session, Depends(get_db)]


def _set_auth_cookies(response: JSONResponse, user_id: int, db: Session) -> None:
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


def _clear_auth_cookies(response: JSONResponse) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(payload: UserCreate, request: Request, db: Db) -> JSONResponse:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return JSONResponse(
            status_code=201,
            content={"message": "If this email is not registered, a verification link has been sent."},
        )
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_verified=False,
        verification_token=_secrets.token_urlsafe(32),
        consent_accepted_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    settings = get_settings()
    verify_url = f"{settings.frontend_url}/auth/verify?token={user.verification_token}"
    send_email(
        email,
        "Подтверждение регистрации — CAOS",
        f"<p>Здравствуйте, {payload.display_name}!</p>"
        f"<p>Для подтверждения регистрации перейдите по ссылке:</p>"
        f"<p><a href=\"{verify_url}\">{verify_url}</a></p>",
    )
    return JSONResponse(
        status_code=201,
        content={"message": "Account created. Check your email for a verification link."},
    )


@router.post("/login")
@limiter.limit("10/minute")
def login(payload: UserLogin, request: Request, db: Db) -> JSONResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Check your email.")
    response = JSONResponse(content={"user": UserOut.model_validate(user).model_dump()})
    _set_auth_cookies(response, user.id, db)
    db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="login", detail=""))
    db.commit()
    return response


@router.post("/logout")
def logout() -> JSONResponse:
    response = JSONResponse(content={"message": "Logged out"})
    _clear_auth_cookies(response)
    return response


@router.post("/refresh")
def refresh_token(request: Request, db: Db) -> JSONResponse:
    refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        user_id, jti = decode_refresh_token(refresh)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session = db.scalar(select(SessionModel).where(SessionModel.jti == jti, SessionModel.revoked == False))
    if not session:
        raise HTTPException(status_code=401, detail="Session revoked or not found")
    session.revoked = True
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    response = JSONResponse(content={"message": "Token refreshed"})
    _set_auth_cookies(response, user.id, db)
    db.commit()
    return response


@router.get("/verify")
def verify_email(token: str, db: Db) -> JSONResponse:
    user = db.scalar(select(User).where(User.verification_token == token))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.is_verified = True
    user.verification_token = None
    db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="email_verified", detail=""))
    db.commit()
    return JSONResponse(content={"message": "Email verified. You can now log in."})


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, db: Db, user: Annotated[User, Depends(current_user)]) -> User:
    user.display_name = payload.display_name
    user.bio = payload.bio
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Db,
    user: Annotated[User, Depends(current_user)],
) -> JSONResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="password_changed", detail=""))
    db.commit()
    return JSONResponse(content={"message": "Password changed"})


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Db) -> JSONResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user:
        user.verification_token = _secrets.token_urlsafe(32)
        db.commit()
        settings = get_settings()
        reset_url = f"{settings.frontend_url}/auth/reset-password?token={user.verification_token}"
        send_email(
            payload.email.lower(),
            "Сброс пароля — CAOS",
            f"<p>Для сброса пароля перейдите по ссылке:</p>"
            f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
            f"<p>Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>",
        )
    return JSONResponse(content={"message": "If this email is registered, a reset link has been sent."})


@router.post("/reset-password/confirm")
def reset_password_confirm(payload: ResetPasswordConfirm, db: Db) -> JSONResponse:
    user = db.scalar(select(User).where(User.verification_token == payload.token))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = hash_password(payload.new_password)
    user.verification_token = None
    db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="password_reset", detail=""))
    db.commit()
    return JSONResponse(content={"message": "Password reset successful. You can now log in."})


@router.get("/me/export")
def export_user_data(db: Db, user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    from ..models import Problem, Goal, Project, Decision, KnowledgeItem, Competence, Task, TeamMember, ProjectMember
    data = {
        "user": UserOut.model_validate(user).model_dump(),
        "problems": [{"id": p.id, "title": p.title, "description": p.description, "status": p.status, "created_at": str(p.created_at)} for p in db.scalars(select(Problem).where(Problem.author_id == user.id))],
        "goals": [{"id": g.id, "title": g.title, "description": g.description, "status": g.status, "created_at": str(g.created_at)} for g in db.scalars(select(Goal).where(Goal.owner_id == user.id))],
        "projects": [{"id": p.id, "title": p.title, "description": p.description, "status": p.status, "created_at": str(p.created_at)} for p in db.scalars(select(Project).where(Project.owner_id == user.id))],
        "decisions": [{"id": d.id, "title": d.title, "proposal": d.proposal, "status": d.status, "created_at": str(d.created_at)} for d in db.scalars(select(Decision).where(Decision.author_id == user.id))],
        "knowledge": [{"id": k.id, "title": k.title, "content": k.content, "created_at": str(k.created_at)} for k in db.scalars(select(KnowledgeItem).where(KnowledgeItem.author_id == user.id))],
        "competences": [{"id": c.id, "name": c.name, "level": c.level, "description": c.description} for c in db.scalars(select(Competence).where(Competence.user_id == user.id))],
    }
    return JSONResponse(content=data)


@router.delete("/me")
def delete_account(db: Db, user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    db.add(AuditEvent(actor_id=user.id, entity_type="user", entity_id=user.id, action="account_deleted", detail=""))
    user.email = f"deleted_{user.id}@deleted.local"
    user.display_name = "Deleted User"
    user.password_hash = None
    user.bio = ""
    user.stepik_id = None
    user.is_verified = False
    user.verification_token = None
    db.commit()
    response = JSONResponse(content={"message": "Account deleted"})
    _clear_auth_cookies(response)
    return response


@router.get("/sessions")
def list_sessions(db: Db, user: Annotated[User, Depends(current_user)]) -> list[dict]:
    sessions = db.scalars(
        select(SessionModel)
        .where(SessionModel.user_id == user.id)
        .order_by(SessionModel.created_at.desc())
        .limit(20)
    )
    return [
        {
            "id": s.id,
            "created_at": str(s.created_at),
            "expires_at": str(s.expires_at),
            "revoked": s.revoked,
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: int, db: Db, user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    session = db.get(SessionModel, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    session.revoked = True
    db.commit()
    return JSONResponse(content={"message": "Session revoked"})
