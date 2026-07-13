from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Notification, User
from ..schemas import NotificationOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Db, user: CurrentUser) -> list[Notification]:
    return list(db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ))


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, db: Db, user: CurrentUser) -> Notification:
    item = db.get(Notification, notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    if item.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    item.is_read = True
    db.commit()
    db.refresh(item)
    return item


@router.patch("/notifications/read-all", status_code=status.HTTP_200_OK)
def mark_all_read(db: Db, user: CurrentUser) -> dict[str, int]:
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    db.commit()
    return {"updated": result.rowcount}
