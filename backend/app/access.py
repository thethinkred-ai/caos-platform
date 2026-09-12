"""Shared access-scope helpers.

Single source of truth for "which projects/goals can this user touch",
previously duplicated across entities.py, search.py and missing in ai.py.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import DomainError, FORBIDDEN_SCOPE
from .models import Goal, GoalParticipation, Project, ProjectGoal, ProjectMember


def user_project_ids(db: Session, user_id: int) -> set[int]:
    """Projects the user owns or is a member of."""
    owned = set(db.scalars(select(Project.id).where(Project.owner_id == user_id)))
    member = set(db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    ))
    return owned | member


def user_goal_ids(db: Session, user_id: int) -> set[int]:
    """Goals the user owns, is a participant of, or that are linked to
    the user's projects (legacy goal_id and project_goals M2M)."""
    owned = set(db.scalars(select(Goal.id).where(Goal.owner_id == user_id)))
    project_ids = user_project_ids(db, user_id)
    project_goal_ids: set[int] = set()
    if project_ids:
        project_goal_ids = set(db.scalars(
            select(Project.goal_id).where(Project.id.in_(project_ids), Project.goal_id.isnot(None))
        ))
        project_goal_ids |= set(db.scalars(
            select(ProjectGoal.goal_id).where(ProjectGoal.project_id.in_(project_ids))
        ))
    participated_goal_ids = set(db.scalars(
        select(GoalParticipation.goal_id).where(
            GoalParticipation.user_id == user_id,
            GoalParticipation.status == "active",
        )
    ))
    return owned | project_goal_ids | participated_goal_ids


def require_goal(db: Session, user_id: int, goal_id: int) -> Goal:
    """Fetch a goal and enforce that the user can access it."""
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal_id not in user_goal_ids(db, user_id):
        raise DomainError(403, FORBIDDEN_SCOPE, "Goal access denied")
    return goal
