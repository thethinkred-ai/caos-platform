from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Competence, User
from ..schemas import CompetenceCreate, CompetenceOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/competences", response_model=list[CompetenceOut])
def list_competences(db: Db, user: CurrentUser) -> list[Competence]:
    return list(db.scalars(
        select(Competence)
        .where(Competence.user_id == user.id)
        .order_by(Competence.created_at.desc())
    ))


@router.post("/competences", response_model=CompetenceOut, status_code=status.HTTP_201_CREATED)
def create_competence(payload: CompetenceCreate, db: Db, user: CurrentUser) -> Competence:
    item = Competence(**payload.model_dump(), user_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/competences/{competence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competence(competence_id: int, db: Db, user: CurrentUser) -> None:
    item = db.get(Competence, competence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Competence not found")
    if item.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(item)
    db.commit()
