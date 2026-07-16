from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, text, func
from sqlalchemy.orm import Session

from ..db import engine, get_db
from ..deps import current_user
from ..models import Decision, Goal, KnowledgeItem, Problem, Project, User
from ..schemas import DecisionOut, KnowledgeOut, SearchResults

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_IS_SQLITE = engine.dialect.name == "sqlite"


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
    if _IS_SQLITE:
        pattern = f"%{q}%"
        problems = list(db.scalars(
            select(Problem).where(or_(Problem.title.ilike(pattern), Problem.description.ilike(pattern))).limit(20)
        ))
        goals = list(db.scalars(
            select(Goal).where(or_(Goal.title.ilike(pattern), Goal.description.ilike(pattern))).limit(20)
        ))
        projects = list(db.scalars(
            select(Project).where(or_(Project.title.ilike(pattern), Project.description.ilike(pattern))).limit(20)
        ))
        knowledge = list(db.scalars(
            select(KnowledgeItem).where(or_(KnowledgeItem.title.ilike(pattern), KnowledgeItem.content.ilike(pattern))).limit(20)
        ))
        decisions = list(db.scalars(
            select(Decision).where(or_(Decision.title.ilike(pattern), Decision.proposal.ilike(pattern))).limit(20)
        ))
    else:
        problems = list(db.scalars(
            select(Problem).where(_fts_match(db, Problem, q, Problem.title, Problem.description)).limit(20)
        ))
        goals = list(db.scalars(
            select(Goal).where(_fts_match(db, Goal, q, Goal.title, Goal.description)).limit(20)
        ))
        projects = list(db.scalars(
            select(Project).where(_fts_match(db, Project, q, Project.title, Project.description)).limit(20)
        ))
        knowledge = list(db.scalars(
            select(KnowledgeItem).where(_fts_match(db, KnowledgeItem, q, KnowledgeItem.title, KnowledgeItem.content)).limit(20)
        ))
        decisions = list(db.scalars(
            select(Decision).where(_fts_match(db, Decision, q, Decision.title, Decision.proposal)).limit(20)
        ))
    return SearchResults(problems=problems, goals=goals, projects=projects, knowledge=knowledge, decisions=decisions)
