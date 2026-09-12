from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, or_, select, func
from sqlalchemy.orm import Session

from ..db import engine, get_db
from ..deps import current_user
from ..models import Decision, Goal, KnowledgeItem, Problem, Project, ProjectMember, User
from ..schemas import SearchResults

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


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _fts_match(q: str, *columns) -> ColumnElement[bool]:
    """Full-text search: plainto_tsquery on PostgreSQL, ILIKE fallback on SQLite."""
    if _IS_SQLITE:
        pattern = f"%{_escape_like(q)}%"
        return or_(*[col.ilike(pattern, escape="\\") for col in columns])
    tsquery = func.plainto_tsquery("simple", q)
    tsvector = func.to_tsvector("simple", func.concat_ws(" ", *columns))
    return tsvector.op("@@")(tsquery)


def _search_entity(db: Session, model, scope: ColumnElement[bool], columns, q: str, limit: int = 20):
    return list(db.scalars(
        select(model).where(scope, _fts_match(q, *columns)).limit(limit)
    ))


@router.get("/search", response_model=SearchResults)
def search(db: Db, user: CurrentUser, q: str = Query(min_length=2, max_length=200)) -> SearchResults:
    project_ids = _user_project_ids(db, user.id)
    goal_ids = _user_goal_ids(db, user.id)

    knowledge_scope: ColumnElement[bool]
    if project_ids:
        knowledge_scope = or_(
            KnowledgeItem.author_id == user.id,
            KnowledgeItem.project_id.in_(project_ids),
        )
    else:
        knowledge_scope = KnowledgeItem.author_id == user.id

    return SearchResults(
        problems=_search_entity(db, Problem, Problem.author_id == user.id, (Problem.title, Problem.description), q),
        goals=_search_entity(db, Goal, Goal.id.in_(goal_ids) if goal_ids else Goal.id == -1, (Goal.title, Goal.description), q),
        projects=_search_entity(db, Project, Project.id.in_(project_ids) if project_ids else Project.id == -1, (Project.title, Project.description), q),
        knowledge=_search_entity(db, KnowledgeItem, knowledge_scope, (KnowledgeItem.title, KnowledgeItem.content), q),
        decisions=_search_entity(db, Decision, Decision.author_id == user.id, (Decision.title, Decision.proposal), q),
    )
