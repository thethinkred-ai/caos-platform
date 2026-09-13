"""Object-level permission matrix (Track D1, ADR-0004).

Resolves the critique's central governance conflict: `owner_id` must not
be the sole source of power. Seeing a goal (access.py) and acting on it
(permissions.py) are different things — capabilities come from the
contextual role in the goal, not from a global user.role.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import DomainError, FORBIDDEN_SCOPE
from .models import Delegation, Goal, GoalParticipation, User

# capability -> roles that hold it in the context of a goal
GOAL_CAPABILITIES: dict[str, set[str]] = {
    "transition": {"owner", "coordinator"},       # lifecycle operations
    "recognize": {"owner", "coordinator"},        # accept / reject a proposal
    "coordinate": {"owner", "coordinator"},       # invite, change roles
    "edit": {"owner", "coordinator"},
    "report_result": {"owner", "coordinator", "facilitator", "contributor"},
    "verify_result": {"owner", "coordinator", "expert"},
    "create_relation": {"owner", "coordinator", "facilitator", "contributor", "expert"},
    "propose_decision": {"owner", "coordinator", "facilitator"},
}


def goal_role(db: Session, user_id: int, goal: Goal) -> str | None:
    """The user's effective role in this goal: 'owner' or an active
    participation role. None means no role (access may still exist via
    project membership — visibility only, no capabilities)."""
    if goal.owner_id == user_id:
        return "owner"
    participation = db.scalar(
        select(GoalParticipation).where(
            GoalParticipation.goal_id == goal.id,
            GoalParticipation.user_id == user_id,
            GoalParticipation.status == "active",
        )
    )
    return participation.role if participation else None


def user_can(db: Session, user: User, goal: Goal, capability: str) -> bool:
    roles = GOAL_CAPABILITIES.get(capability)
    if roles is None:
        raise ValueError(f"Unknown capability: {capability}")
    role = goal_role(db, user.id, goal)
    if role in roles:
        return True
    # INV-7: an active delegation grants the capability for its scope and
    # term only — never permanently.
    now = datetime.now(UTC)
    delegation = db.scalar(
        select(Delegation.id).where(
            Delegation.recipient_id == user.id,
            Delegation.goal_id == goal.id,
            Delegation.capability == capability,
            Delegation.revoked_at.is_(None),
            Delegation.valid_from <= now,
            Delegation.valid_until > now,
        ).limit(1)
    )
    return delegation is not None


def require_capability(db: Session, user: User, goal: Goal, capability: str) -> None:
    if not user_can(db, user, goal, capability):
        raise DomainError(
            403, FORBIDDEN_SCOPE,
            f"Requires one of roles {sorted(GOAL_CAPABILITIES[capability])} in this goal",
        )


def has_multiple_participants(db: Session, goal: Goal) -> bool:
    """True when people besides the owner actively participate — the case
    where collective recognition (an accepted decision) is required."""
    count = len(list(db.scalars(
        select(GoalParticipation.id).where(
            GoalParticipation.goal_id == goal.id,
            GoalParticipation.status == "active",
            GoalParticipation.user_id != goal.owner_id,
        )
    )))
    return count > 0


def goal_has_accepted_decision(db: Session, goal: Goal) -> bool:
    from .models import Decision

    return db.scalar(
        select(Decision.id).where(Decision.goal_id == goal.id, Decision.status == "accepted").limit(1)
    ) is not None
