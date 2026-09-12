"""Commitment endpoints (Track C4).

A commitment is a voluntarily accepted obligation of concrete work
towards a goal — the answer to "who actually took responsibility for
this part of the goal", as opposed to an assigned task.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Commitment, GoalParticipation, Notification, User
from ..schemas import CommitmentCreate, CommitmentStatusUpdate

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "withdrawn"},
    "in_progress": {"fulfilled", "failed", "withdrawn"},
}


def _out(c: Commitment, display_name: str) -> dict:
    return {
        "id": c.id,
        "goal_id": c.goal_id,
        "user_id": c.user_id,
        "display_name": display_name,
        "description": c.description,
        "expected_result": c.expected_result,
        "deadline": c.deadline.isoformat() if c.deadline else None,
        "source": c.source,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
    }


def _ensure_participation(db: Session, goal_id: int, user_id: int) -> None:
    """A commitment implies participation: auto-join as contributor."""
    existing = db.scalar(
        select(GoalParticipation).where(
            GoalParticipation.goal_id == goal_id, GoalParticipation.user_id == user_id
        )
    )
    if existing is None:
        db.add(GoalParticipation(goal_id=goal_id, user_id=user_id, role="contributor"))
    elif existing.status != "active":
        existing.status = "active"
        existing.left_at = None


@router.post("/goals/{goal_id}/commitments", status_code=status.HTTP_201_CREATED)
def create_commitment(goal_id: int, payload: CommitmentCreate, db: Db, user: CurrentUser) -> dict:
    require_goal(db, user.id, goal_id)
    _ensure_participation(db, goal_id, user.id)

    commitment = Commitment(
        goal_id=goal_id,
        user_id=user.id,
        description=payload.description,
        expected_result=payload.expected_result,
        deadline=payload.deadline,
        source="self",
    )
    db.add(commitment)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="commitment", entity_id=commitment.id,
        action="created", detail=payload.description[:100],
    ))
    db.commit()
    return _out(commitment, user.display_name)


@router.get("/goals/{goal_id}/commitments")
def list_goal_commitments(goal_id: int, db: Db, user: CurrentUser) -> list[dict]:
    require_goal(db, user.id, goal_id)
    rows = db.execute(
        select(Commitment, User.display_name)
        .join(User, User.id == Commitment.user_id)
        .where(Commitment.goal_id == goal_id)
        .order_by(Commitment.created_at.desc())
    ).all()
    return [_out(c, name) for c, name in rows]


@router.get("/commitments/my")
def my_commitments(db: Db, user: CurrentUser) -> list[dict]:
    rows = db.execute(
        select(Commitment, User.display_name)
        .join(User, User.id == Commitment.user_id)
        .where(Commitment.user_id == user.id)
        .order_by(Commitment.created_at.desc())
    ).all()
    return [_out(c, name) for c, name in rows]


@router.post("/commitments/{commitment_id}/status")
def update_commitment_status(
    commitment_id: int, payload: CommitmentStatusUpdate, db: Db, user: CurrentUser
) -> dict:
    commitment = db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    if commitment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can update a commitment")

    allowed = _STATUS_TRANSITIONS.get(commitment.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move commitment from '{commitment.status}' to '{payload.status}'. Allowed: {sorted(allowed)}",
        )
    commitment.status = payload.status
    db.add(AuditEvent(
        actor_id=user.id, entity_type="commitment", entity_id=commitment_id,
        action=payload.status, detail=commitment.description[:100],
    ))
    db.add(Notification(
        user_id=user.id, entity_type="commitment", entity_id=commitment_id,
        message=f"Commitment '{commitment.description[:60]}' is now {payload.status}",
    ))
    db.commit()
    return _out(commitment, user.display_name)
