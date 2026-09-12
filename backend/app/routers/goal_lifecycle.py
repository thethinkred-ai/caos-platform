"""Goal lifecycle state machine (Track C2).

Today a goal is created as draft and no endpoint can ever change its
status. This router introduces server-validated transitions: the status
graph of ontology.md, executed only through explicit commands (invariant
INV-1: no free-form status patching).

Until Track C5 lands, `report_achieved`/`verify` are claims by the owner;
they become evidence-gated (Result + verifier) in C5.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Goal, Notification, User
from ..schemas import GoalOut, GoalTransition

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

# action -> (allowed source statuses, resulting status)
GOAL_TRANSITIONS: dict[str, tuple[set[str], str]] = {
    "propose": ({"draft"}, "proposed"),
    "review": ({"proposed"}, "under_review"),
    "accept": ({"proposed", "under_review"}, "accepted"),
    "reject": ({"proposed", "under_review"}, "rejected"),
    "activate": ({"accepted"}, "active"),
    "suspend": ({"active"}, "suspended"),
    "resume": ({"suspended"}, "active"),
    "report-achieved": ({"active"}, "achieved"),
    "verify": ({"achieved"}, "verified"),
    "abandon": ({"accepted", "active", "suspended"}, "abandoned"),
    "supersede": ({"accepted", "active", "suspended"}, "superseded"),
    "close": ({"verified", "rejected", "abandoned", "superseded"}, "closed"),
}


@router.post("/goals/{goal_id}/transition", response_model=GoalOut)
def transition_goal(goal_id: int, payload: GoalTransition, db: Db, user: CurrentUser) -> Goal:
    goal = require_goal(db, user.id, goal_id)
    # Ownership for now; the participation permission matrix arrives with C3/D1.
    if goal.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the goal owner can change the goal state")

    if payload.action not in GOAL_TRANSITIONS:
        raise HTTPException(status_code=422, detail=f"Unknown action. Valid: {sorted(GOAL_TRANSITIONS)}")
    allowed_from, target = GOAL_TRANSITIONS[payload.action]
    if goal.status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot '{payload.action}' from status '{goal.status}'. Allowed from: {sorted(allowed_from)}",
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
            raise HTTPException(
                status_code=409,
                detail="Goal cannot be reported achieved without a verified result "
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
