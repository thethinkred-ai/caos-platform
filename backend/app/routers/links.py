"""Project-goal M2M links and knowledge relations (Track C7)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Goal, KnowledgeItem, KnowledgeRelation, Project, ProjectGoal, User
from ..schemas import (
    KnowledgeOut, KnowledgeRelationCreate, KnowledgeRelationOut,
    ProjectGoalCreate, ProjectGoalOut,
)

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_KNOWLEDGE_TARGETS = {"problem", "goal", "decision", "result"}
_KNOWLEDGE_RELATIONS = {"supports", "explains", "evidences", "relates", "contradicts"}


# --- project <-> goal ---


@router.get("/projects/{project_id}/goals", response_model=list[ProjectGoalOut])
def list_project_goals(project_id: int, db: Db, user: CurrentUser) -> list[ProjectGoal]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and not db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    ):
        from ..errors import DomainError, FORBIDDEN_SCOPE

        raise DomainError(403, FORBIDDEN_SCOPE, "Project membership required")
    return list(db.scalars(
        select(ProjectGoal).where(ProjectGoal.project_id == project_id).order_by(ProjectGoal.created_at)
    ))


@router.post("/projects/{project_id}/goals", response_model=ProjectGoalOut, status_code=status.HTTP_201_CREATED)
def link_project_goal(project_id: int, payload: ProjectGoalCreate, db: Db, user: CurrentUser) -> ProjectGoal:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can link goals")
    require_goal(db, user.id, payload.goal_id)  # the project may only serve goals the owner can access

    duplicate = db.scalar(
        select(ProjectGoal).where(ProjectGoal.project_id == project_id, ProjectGoal.goal_id == payload.goal_id)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="This project is already linked to the goal")

    link = ProjectGoal(project_id=project_id, created_by=user.id, **payload.model_dump())
    db.add(link)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="project_goal", entity_id=link.id,
        action="linked", detail=f"project {project_id} -> goal {payload.goal_id}",
    ))
    db.commit()
    db.refresh(link)
    return link


# --- knowledge relations ---


def _require_knowledge_access(db: Session, user: User, knowledge_id: int) -> KnowledgeItem:
    from ..access import user_project_ids

    item = db.get(KnowledgeItem, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    if item.author_id != user.id and (
        item.project_id is None or item.project_id not in user_project_ids(db, user.id)
    ):
        from ..errors import DomainError, FORBIDDEN_SCOPE

        raise DomainError(403, FORBIDDEN_SCOPE, "Knowledge access denied")
    return item


def _require_target_visible(db: Session, user: User, target_type: str, target_id: int) -> None:
    if target_type == "goal":
        require_goal(db, user.id, target_id)
    elif target_type == "problem":
        from ..models import Problem

        problem = db.get(Problem, target_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Problem not found")
        if problem.author_id != user.id:
            raise HTTPException(status_code=403, detail="Problem access denied")
    elif target_type == "decision":
        from ..models import Decision

        decision = db.get(Decision, target_id)
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        if decision.goal_id:
            require_goal(db, user.id, decision.goal_id)
        elif decision.author_id != user.id:
            raise HTTPException(status_code=403, detail="Decision access denied")
    elif target_type == "result":
        from ..models import Result

        result = db.get(Result, target_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        require_goal(db, user.id, result.goal_id)


@router.post("/knowledge/{knowledge_id}/relations", response_model=KnowledgeRelationOut, status_code=status.HTTP_201_CREATED)
def link_knowledge(knowledge_id: int, payload: KnowledgeRelationCreate, db: Db, user: CurrentUser) -> KnowledgeRelation:
    if payload.target_type not in _KNOWLEDGE_TARGETS:
        raise HTTPException(status_code=422, detail=f"target_type must be one of {sorted(_KNOWLEDGE_TARGETS)}")
    if payload.relation_type not in _KNOWLEDGE_RELATIONS:
        raise HTTPException(status_code=422, detail=f"relation_type must be one of {sorted(_KNOWLEDGE_RELATIONS)}")
    _require_knowledge_access(db, user, knowledge_id)
    _require_target_visible(db, user, payload.target_type, payload.target_id)

    duplicate = db.scalar(
        select(KnowledgeRelation).where(
            KnowledgeRelation.knowledge_id == knowledge_id,
            KnowledgeRelation.target_type == payload.target_type,
            KnowledgeRelation.target_id == payload.target_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="This relation already exists")

    relation = KnowledgeRelation(knowledge_id=knowledge_id, created_by=user.id, **payload.model_dump())
    db.add(relation)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="knowledge_relation", entity_id=relation.id,
        action="linked", detail=f"{payload.relation_type} {payload.target_type}#{payload.target_id}",
    ))
    db.commit()
    db.refresh(relation)
    return relation


@router.get("/knowledge/{knowledge_id}/relations", response_model=list[KnowledgeRelationOut])
def list_knowledge_relations(knowledge_id: int, db: Db, user: CurrentUser) -> list[KnowledgeRelation]:
    _require_knowledge_access(db, user, knowledge_id)
    return list(db.scalars(
        select(KnowledgeRelation).where(KnowledgeRelation.knowledge_id == knowledge_id)
        .order_by(KnowledgeRelation.created_at)
    ))
