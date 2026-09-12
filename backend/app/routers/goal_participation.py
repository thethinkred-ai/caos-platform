"""Goal participation endpoints (Track C3, ADR-0004).

Participation is a person's contextual relation to a goal; it is also an
access path: an active participant can see and work with the goal even
without any project membership.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..permissions import require_capability
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, GoalParticipation, User
from ..schemas import GoalParticipationCreate, GoalParticipationRoleUpdate

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_ROLES = {"contributor", "coordinator", "expert", "facilitator", "observer"}


def _participation_payload(p: GoalParticipation, display_name: str) -> dict:
    return {
        "id": p.id,
        "goal_id": p.goal_id,
        "user_id": p.user_id,
        "display_name": display_name,
        "role": p.role,
        "status": p.status,
        "joined_at": p.joined_at.isoformat(),
        "left_at": p.left_at.isoformat() if p.left_at else None,
    }


@router.get("/goals/{goal_id}/participations")
def list_participations(goal_id: int, db: Db, user: CurrentUser) -> list[dict]:
    require_goal(db, user.id, goal_id)
    rows = db.execute(
        select(GoalParticipation, User.display_name)
        .join(User, User.id == GoalParticipation.user_id)
        .where(GoalParticipation.goal_id == goal_id)
        .order_by(GoalParticipation.joined_at)
    ).all()
    return [_participation_payload(p, name) for p, name in rows]


@router.post("/goals/{goal_id}/participations", status_code=status.HTTP_201_CREATED)
def join_goal(goal_id: int, payload: GoalParticipationCreate, db: Db, user: CurrentUser) -> dict:
    goal = require_goal(db, user.id, goal_id)
    if payload.role not in _ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Valid: {sorted(_ROLES)}")

    target_user_id = payload.user_id
    if target_user_id is not None and target_user_id != user.id:
        # Inviting someone else requires the coordinate capability.
        require_capability(db, user, goal, "coordinate")
        if not db.get(User, target_user_id):
            raise HTTPException(status_code=404, detail="User not found")

    effective_user_id = target_user_id or user.id
    existing = db.scalar(
        select(GoalParticipation).where(
            GoalParticipation.goal_id == goal_id, GoalParticipation.user_id == effective_user_id
        )
    )
    if existing:
        if existing.status == "active":
            raise HTTPException(status_code=409, detail="Already a participant")
        # Re-joining after leaving reactivates the same record (history kept).
        existing.status = "active"
        existing.role = payload.role
        existing.left_at = None
        db.flush()
        db.add(AuditEvent(actor_id=user.id, entity_type="goal_participation", entity_id=existing.id, action="rejoined", detail=""))
        db.commit()
        return _participation_payload(existing, db.get(User, effective_user_id).display_name)

    participation = GoalParticipation(goal_id=goal_id, user_id=effective_user_id, role=payload.role)
    db.add(participation)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="goal_participation", entity_id=participation.id,
        action="joined", detail=f"role={payload.role}",
    ))
    db.commit()
    return _participation_payload(participation, db.get(User, effective_user_id).display_name)


@router.post("/goals/{goal_id}/participations/leave")
def leave_goal(goal_id: int, db: Db, user: CurrentUser) -> dict:
    require_goal(db, user.id, goal_id)
    participation = db.scalar(
        select(GoalParticipation).where(
            GoalParticipation.goal_id == goal_id,
            GoalParticipation.user_id == user.id,
            GoalParticipation.status == "active",
        )
    )
    if not participation:
        raise HTTPException(status_code=404, detail="Active participation not found")
    participation.status = "left"
    participation.left_at = datetime.now(UTC)
    db.add(AuditEvent(actor_id=user.id, entity_type="goal_participation", entity_id=participation.id, action="left", detail=""))
    db.commit()
    return {"message": "Left the goal"}


@router.patch("/goals/{goal_id}/participations/{user_id}")
def update_participation_role(
    goal_id: int, user_id: int, payload: GoalParticipationRoleUpdate, db: Db, user: CurrentUser
) -> dict:
    goal = require_goal(db, user.id, goal_id)
    require_capability(db, user, goal, "coordinate")
    if payload.role not in _ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Valid: {sorted(_ROLES)}")
    participation = db.scalar(
        select(GoalParticipation).where(
            GoalParticipation.goal_id == goal_id,
            GoalParticipation.user_id == user_id,
            GoalParticipation.status == "active",
        )
    )
    if not participation:
        raise HTTPException(status_code=404, detail="Active participation not found")
    participation.role = payload.role
    db.add(AuditEvent(
        actor_id=user.id, entity_type="goal_participation", entity_id=participation.id,
        action="role_changed", detail=payload.role,
    ))
    db.commit()
    return _participation_payload(participation, db.get(User, user_id).display_name)
