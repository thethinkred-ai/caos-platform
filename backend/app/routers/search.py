from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Decision, Goal, KnowledgeItem, Problem, Project, User
from ..schemas import DecisionOut, KnowledgeOut, SearchResults

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/search", response_model=SearchResults)
def search(db: Db, user: CurrentUser, q: str = Query(min_length=2, max_length=200)) -> SearchResults:
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
    return SearchResults(problems=problems, goals=goals, projects=projects, knowledge=knowledge, decisions=decisions)
