from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, text, func
from sqlalchemy.orm import Session

from ..db import engine, get_db
from ..deps import current_user
from ..models import Decision, Goal, KnowledgeItem, Problem, Project, ProjectMember, User
from ..schemas import DecisionOut, KnowledgeOut, SearchResults

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_IS_SQLITE = engine.dialect.name == "sqlite"


def _user_project_ids(db: Session, user_id: int) -> set[int]:
    owned = set(db.scalars(select(Project.id).where(Project.owner_id == user_id)))
    member = set(db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    ))
    return owned | member


def _user_goal_ids(db: Session, user_id: int) -> set[int]:
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


def _fts_match(db, model, q: str, *columns):
    """Full-text search: uses plainto_tsquery on PostgreSQL, ILIKE fallback on SQLite."""
    if _IS_SQLITE:
        pattern = f"%{q}%"
        return or_(*[col.ilike(pattern) for col in columns])
    tsquery = func.plainto_tsquery("simple", q)
    tsvector = func.to_tsvector("simple", func.coalesce(columns[0], "") + " " + func.coalesce(columns[1], ""))
    return tsvector.op("@@")(tsquery)


@router.get("/search", response_model=SearchResults)
def search(db: Db, user: CurrentUser, q: str = Query(min_length=2, max_length=200)) -> SearchResults:
    project_ids = _user_project_ids(db, user.id)
    goal_ids = _user_goal_ids(db, user.id)
    if _IS_SQLITE:
        pattern = f"%{q}%"
        problems = list(db.scalars(
            select(Problem).where(
                Problem.author_id == user.id,
                or_(Problem.title.ilike(pattern), Problem.description.ilike(pattern))
            ).limit(20)
        ))
        goals = list(db.scalars(
            select(Goal).where(
                Goal.id.in_(goal_ids) if goal_ids else Goal.id == -1,
                or_(Goal.title.ilike(pattern), Goal.description.ilike(pattern))
            ).limit(20)
        ))
        projects = list(db.scalars(
            select(Project).where(
                Project.id.in_(project_ids) if project_ids else Project.id == -1,
                or_(Project.title.ilike(pattern), Project.description.ilike(pattern))
            ).limit(20)
        ))
        knowledge = list(db.scalars(
            select(KnowledgeItem).where(
                (KnowledgeItem.author_id == user.id) | (KnowledgeItem.project_id.in_(project_ids)) if project_ids else KnowledgeItem.author_id == user.id,
                or_(KnowledgeItem.title.ilike(pattern), KnowledgeItem.content.ilike(pattern))
            ).limit(20)
        ))
        decisions = list(db.scalars(
            select(Decision).where(
                Decision.author_id == user.id,
                or_(Decision.title.ilike(pattern), Decision.proposal.ilike(pattern))
            ).limit(20)
        ))
    else:
        problems = list(db.scalars(
            select(Problem).where(
                Problem.author_id == user.id,
                _fts_match(db, Problem, q, Problem.title, Problem.description)
            ).limit(20)
        ))
        goals = list(db.scalars(
            select(Goal).where(
                Goal.id.in_(goal_ids) if goal_ids else Goal.id == -1,
                _fts_match(db, Goal, q, Goal.title, Goal.description)
            ).limit(20)
        ))
        projects = list(db.scalars(
            select(Project).where(
                Project.id.in_(project_ids) if project_ids else Project.id == -1,
                _fts_match(db, Project, q, Project.title, Project.description)
            ).limit(20)
        ))
        knowledge = list(db.scalars(
            select(KnowledgeItem).where(
                (KnowledgeItem.author_id == user.id) | (KnowledgeItem.project_id.in_(project_ids)) if project_ids else KnowledgeItem.author_id == user.id,
                _fts_match(db, KnowledgeItem, q, KnowledgeItem.title, KnowledgeItem.content)
            ).limit(20)
        ))
        decisions = list(db.scalars(
            select(Decision).where(
                Decision.author_id == user.id,
                _fts_match(db, Decision, q, Decision.title, Decision.proposal)
            ).limit(20)
        ))
    return SearchResults(problems=problems, goals=goals, projects=projects, knowledge=knowledge, decisions=decisions)
