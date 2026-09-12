"""Challenge endpoints (Track C6): a structured objection to a goal,
decision or result. An objection is an object — it cannot be lost, and
resolving it requires a recorded answer.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal, user_goal_ids
from ..db import get_db
from ..deps import current_user
from ..errors import CHALLENGE_ALREADY_RESOLVED, DomainError, FORBIDDEN_SCOPE
from ..models import AuditEvent, Challenge, Decision, Goal, Result, User
from ..schemas import ChallengeCreate, ChallengeOut, ChallengeResolve

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_TARGET_TYPES = {"goal", "decision", "result"}
_RESOLUTION_STATUSES = {"acknowledged", "addressed", "accepted", "rejected", "deferred", "withdrawn"}


def _require_target_access(db: Session, user: User, target_type: str, target_id: int) -> None:
    """The challenger must be able to see what they are challenging."""
    if target_type == "goal":
        require_goal(db, user.id, target_id)
    elif target_type == "decision":
        decision = db.get(Decision, target_id)
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        if decision.goal_id:
            require_goal(db, user.id, decision.goal_id)
        elif decision.author_id != user.id:
            raise HTTPException(status_code=403, detail="Decision access denied")
    elif target_type == "result":
        result = db.get(Result, target_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        require_goal(db, user.id, result.goal_id)


def _counterpart_id(db: Session, challenge: Challenge) -> int | None:
    """Who is being challenged: goal owner / decision author / the owner
    of the goal the result belongs to."""
    if challenge.target_type == "goal":
        goal = db.get(Goal, challenge.target_id)
        return goal.owner_id if goal else None
    if challenge.target_type == "decision":
        decision = db.get(Decision, challenge.target_id)
        return decision.author_id if decision else None
    if challenge.target_type == "result":
        result = db.get(Result, challenge.target_id)
        if not result:
            return None
        goal = db.get(Goal, result.goal_id)
        return goal.owner_id if goal else None
    return None


@router.post("/challenges", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
def create_challenge(payload: ChallengeCreate, db: Db, user: CurrentUser) -> Challenge:
    if payload.target_type not in _TARGET_TYPES:
        raise HTTPException(status_code=422, detail=f"target_type must be one of {sorted(_TARGET_TYPES)}")
    _require_target_access(db, user, payload.target_type, payload.target_id)

    challenge = Challenge(author_id=user.id, **payload.model_dump())
    db.add(challenge)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="challenge", entity_id=challenge.id,
        action="created", detail=f"{payload.target_type}#{payload.target_id}: {payload.claim[:80]}",
    ))
    db.commit()
    db.refresh(challenge)
    return challenge


@router.get("/challenges", response_model=list[ChallengeOut])
def list_challenges(
    db: Db,
    user: CurrentUser,
    target_type: str | None = Query(default=None),
    target_id: int | None = Query(default=None),
    mine: bool = Query(default=False),
) -> list[Challenge]:
    query = select(Challenge).order_by(Challenge.created_at.desc()).limit(100)
    if mine:
        query = query.where(Challenge.author_id == user.id)
    elif target_type and target_id:
        _require_target_access(db, user, target_type, target_id)
        query = query.where(Challenge.target_type == target_type, Challenge.target_id == target_id)
    else:
        # Without filters: challenges on goals accessible to the user.
        goal_ids = user_goal_ids(db, user.id)
        condition = Challenge.target_id.in_(goal_ids) if goal_ids else Challenge.target_id == -1
        query = query.where(Challenge.target_type == "goal", condition)
    return list(db.scalars(query))


@router.post("/challenges/{challenge_id}/resolve", response_model=ChallengeOut)
def resolve_challenge(challenge_id: int, payload: ChallengeResolve, db: Db, user: CurrentUser) -> Challenge:
    challenge = db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.status in ("accepted", "rejected", "withdrawn"):
        raise DomainError(409, CHALLENGE_ALREADY_RESOLVED, f"Challenge already resolved as '{challenge.status}'")
    if payload.status not in _RESOLUTION_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_RESOLUTION_STATUSES)}")

    is_author = challenge.author_id == user.id
    counterpart_id = _counterpart_id(db, challenge)

    if payload.status == "withdrawn":
        if not is_author:
            raise HTTPException(status_code=422, detail="Only the author can withdraw a challenge")
    elif user.id != counterpart_id:
        raise DomainError(403, FORBIDDEN_SCOPE, "Only the challenged counterpart can resolve")

    challenge.status = payload.status
    challenge.resolution = payload.resolution
    if payload.status in ("accepted", "rejected", "withdrawn", "addressed"):
        challenge.resolved_at = datetime.now(UTC)
    db.add(AuditEvent(
        actor_id=user.id, entity_type="challenge", entity_id=challenge.id,
        action=payload.status, detail=payload.resolution[:100],
    ))
    db.commit()
    db.refresh(challenge)
    return challenge
