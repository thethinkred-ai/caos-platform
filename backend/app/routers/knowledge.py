from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, KnowledgeItem, Project, User
from ..schemas import KnowledgeCreate, KnowledgeOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/knowledge", response_model=list[KnowledgeOut])
def list_knowledge(db: Db, user: CurrentUser, project_id: int | None = None) -> list[dict]:
    query = (
        select(KnowledgeItem, Project.title.label("project_name"))
        .outerjoin(Project, Project.id == KnowledgeItem.project_id)
        .order_by(KnowledgeItem.created_at.desc())
    )
    if project_id is not None:
        query = query.where(KnowledgeItem.project_id == project_id)
    rows = db.execute(query).all()
    result = []
    for item, project_name in rows:
        d = {c.name: getattr(item, c.name) for c in KnowledgeItem.__table__.columns}
        d["project_name"] = project_name
        result.append(d)
    return result


@router.post("/knowledge", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def create_knowledge(payload: KnowledgeCreate, db: Db, user: CurrentUser) -> KnowledgeItem:
    if payload.project_id and not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    item = KnowledgeItem(**payload.model_dump(), author_id=user.id)
    db.add(item)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, entity_type="knowledge", entity_id=item.id, action="created", detail=item.title))
    db.commit()
    db.refresh(item)
    return item
