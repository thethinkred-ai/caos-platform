"""Shared access-scope helpers.

Single source of truth for "which projects/goals can this user touch",
previously duplicated across entities.py, search.py and missing in ai.py.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Goal, Project, ProjectMember


def user_project_ids(db: Session, user_id: int) -> set[int]:
    """Projects the user owns or is a member of."""
    owned = set(db.scalars(select(Project.id).where(Project.owner_id == user_id)))
    member = set(db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    ))
    return owned | member


def user_goal_ids(db: Session, user_id: int) -> set[int]:
    """Goals the user owns or that are linked to the user's projects."""
    owned = set(db.scalars(select(Goal.id).where(Goal.owner_id == user_id)))
    project_goal_ids = set(db.scalars(
        select(Project.goal_id).where(Project.owner_id == user_id, Project.goal_id.isnot(None))
    ))
    member_goal_ids = set(db.scalars(
        select(Project.goal_id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id, Project.goal_id.isnot(None))
    ))
    return owned | project_goal_ids | member_goal_ids


def require_goal(db: Session, user_id: int, goal_id: int) -> Goal:
    """Fetch a goal and enforce that the user can access it."""
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal_id not in user_goal_ids(db, user_id):
        raise HTTPException(status_code=403, detail="Goal access denied")
    return goal
