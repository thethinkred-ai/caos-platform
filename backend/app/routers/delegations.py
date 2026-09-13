"""Delegation endpoints (Track H1, INV-7).

You can only delegate a capability you currently hold yourself, the
scope is always one goal, the expiry is mandatory, and revocation is
cheaper than granting: the issuer or the goal owner revokes at any
moment.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Delegation, Goal, User, UserProfile
from ..permissions import GOAL_CAPABILITIES, goal_role
from ..schemas import DelegationCreate, DelegationOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

# Only operational capabilities are delegatable; governance-level power
# (recognition) is never transferred by a single person.
DELEGATABLE = {"coordinate", "transition", "verify_result"}


def _is_active(delegation: Delegation, now: datetime) -> bool:
    return (
        delegation.revoked_at is None
        and delegation.valid_from <= now
        and delegation.valid_until > now
    )


@router.get("/goals/{goal_id}/delegations", response_model=list[DelegationOut])
def list_delegations(goal_id: int, db: Db, user: CurrentUser) -> list[dict]:
    require_goal(db, user.id, goal_id)
    recipient_profile = aliased(UserProfile)
    issuer_profile = aliased(UserProfile)
    rows = db.execute(
        select(
            Delegation,
            func.coalesce(recipient_profile.display_name, ""),
            func.coalesce(issuer_profile.display_name, ""),
        )
        .outerjoin(recipient_profile, recipient_profile.user_id == Delegation.recipient_id)
        .outerjoin(issuer_profile, issuer_profile.user_id == Delegation.issuer_id)
        .where(Delegation.goal_id == goal_id)
        .order_by(Delegation.created_at.desc())
    ).all()
    now = datetime.now(UTC)
    result = []
    for delegation, recipient_name, issuer_name in rows:
        item = DelegationOut.model_validate(delegation).model_dump(mode="json")
        item["recipient_display_name"] = recipient_name
        item["issuer_display_name"] = issuer_name
        item["is_active"] = _is_active(delegation, now)
        result.append(item)
    return result


@router.post("/goals/{goal_id}/delegations", response_model=DelegationOut, status_code=status.HTTP_201_CREATED)
def create_delegation(goal_id: int, payload: DelegationCreate, db: Db, user: CurrentUser) -> Delegation:
    goal = require_goal(db, user.id, goal_id)
    if payload.capability not in DELEGATABLE:
        raise HTTPException(status_code=422, detail=f"capability must be one of {sorted(DELEGATABLE)}")

    # You can only delegate what you hold yourself right now.
    role = goal_role(db, user.id, goal)
    if role not in GOAL_CAPABILITIES.get(payload.capability, set()):
        raise HTTPException(status_code=403, detail=f"You do not hold the '{payload.capability}' capability in this goal")

    if payload.recipient_id == user.id:
        raise HTTPException(status_code=422, detail="You cannot delegate to yourself")
    if not db.get(User, payload.recipient_id):
        raise HTTPException(status_code=404, detail="Recipient user not found")
    now = datetime.now(UTC)
    if payload.valid_until <= now:
        raise HTTPException(status_code=422, detail="valid_until must be in the future")

    delegation = Delegation(
        goal_id=goal_id,
        issuer_id=user.id,
        recipient_id=payload.recipient_id,
        capability=payload.capability,
        reason=payload.reason,
        valid_until=payload.valid_until,
    )
    db.add(delegation)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="delegation", entity_id=delegation.id,
        action="granted", detail=f"{payload.capability} -> user {payload.recipient_id} until {payload.valid_until:%Y-%m-%d}",
    ))
    db.commit()
    db.refresh(delegation)
    return delegation


@router.post("/delegations/{delegation_id}/revoke", response_model=DelegationOut)
def revoke_delegation(delegation_id: int, db: Db, user: CurrentUser) -> Delegation:
    delegation = db.get(Delegation, delegation_id)
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    goal = db.get(Goal, delegation.goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    if user.id != delegation.issuer_id and goal.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the issuer or the goal owner can revoke")
    if delegation.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Delegation already revoked")

    delegation.revoked_at = datetime.now(UTC)
    delegation.revoked_by = user.id
    db.add(AuditEvent(
        actor_id=user.id, entity_type="delegation", entity_id=delegation.id,
        action="revoked", detail=delegation.capability,
    ))
    db.commit()
    db.refresh(delegation)
    return delegation
