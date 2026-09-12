"""Goal lifecycle state machine (Track C2 + D1).

Server-validated transitions (INV-1: no free-form status patching).
Since D1 the owner is no longer the sole source of power: operational
transitions belong to the goal's owner or a coordinator, and accepting
a proposed goal requires collective recognition — an accepted Decision
linked to the goal — whenever other people actively participate.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..errors import ACHIEVEMENT_REQUIRES_VERIFIED_RESULT, DomainError, INVALID_STATE_TRANSITION
from ..models import AuditEvent, Goal, Notification, User
from ..permissions import (
    goal_has_accepted_decision,
    has_multiple_participants,
    require_capability,
)
from ..schemas import GoalOut, GoalTransition

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

# action -> (allowed source statuses, resulting status, capability)
GOAL_TRANSITIONS: dict[str, tuple[set[str], str, str]] = {
    "propose": ({"draft"}, "proposed", "edit"),
    "review": ({"proposed"}, "under_review", "edit"),
    "accept": ({"proposed", "under_review"}, "accepted", "recognize"),
    "reject": ({"proposed", "under_review"}, "rejected", "recognize"),
    "activate": ({"accepted"}, "active", "transition"),
    "suspend": ({"active"}, "suspended", "transition"),
    "resume": ({"suspended"}, "active", "transition"),
    "report-achieved": ({"active"}, "achieved", "transition"),
    "verify": ({"achieved"}, "verified", "transition"),
    "abandon": ({"accepted", "active", "suspended"}, "abandoned", "transition"),
    "supersede": ({"accepted", "active", "suspended"}, "superseded", "transition"),
    "close": ({"verified", "rejected", "abandoned", "superseded"}, "closed", "transition"),
}


@router.post("/goals/{goal_id}/transition", response_model=GoalOut)
def transition_goal(goal_id: int, payload: GoalTransition, db: Db, user: CurrentUser) -> Goal:
    goal = require_goal(db, user.id, goal_id)

    if payload.action not in GOAL_TRANSITIONS:
        raise HTTPException(status_code=422, detail=f"Unknown action. Valid: {sorted(GOAL_TRANSITIONS)}")
    allowed_from, target, capability = GOAL_TRANSITIONS[payload.action]
    if goal.status not in allowed_from:
        raise DomainError(
            409, INVALID_STATE_TRANSITION,
            f"Cannot '{payload.action}' from status '{goal.status}'. Allowed from: {sorted(allowed_from)}",
        )

    require_capability(db, user, goal, capability)

    # Collective recognition: when other people participate, accepting a
    # goal requires an accepted Decision linked to it — the owner alone
    # cannot recognize a shared goal.
    if payload.action in ("accept", "reject") and has_multiple_participants(db, goal):
        if not goal_has_accepted_decision(db, goal):
            raise DomainError(
                409, "RECOGNITION_REQUIRED",
                "A goal with active participants is accepted only through a collective decision: "
                "create a decision on this goal, vote and finalize it first",
            )

    # INV-3: a goal is achieved only through a result verified by another
    # participant — completing tasks is never enough.
    if payload.action == "report-achieved":
        from sqlalchemy import select

        from ..models import Result

        has_verified = db.scalar(
            select(Result.id).where(
                Result.goal_id == goal_id,
                Result.status.in_(("verified", "partially_verified")),
            ).limit(1)
        )
        if not has_verified:
            raise DomainError(
                409, ACHIEVEMENT_REQUIRES_VERIFIED_RESULT,
                "Goal cannot be reported achieved without a verified result "
                "(report a result under /goals/{id}/results and have another participant verify it)",
            )

    goal.status = target
    db.add(AuditEvent(
        actor_id=user.id, entity_type="goal", entity_id=goal.id,
        action=f"goal:{payload.action}", detail=goal.title,
    ))
    db.add(Notification(
        user_id=user.id, entity_type="goal", entity_id=goal.id,
        message=f"Goal '{goal.title}' is now {target}",
    ))
    db.commit()
    db.refresh(goal)
    return goal
