from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..errors import DomainError, INVALID_STATE_TRANSITION
from ..models import Commitment, Competence, CompetenceEvidence, Result, User
from ..schemas import CompetenceCreate, CompetenceEvidenceCreate, CompetenceEvidenceOut, CompetenceOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/competences")
def list_competences(db: Db, user: CurrentUser) -> list[dict]:
    rows = db.execute(
        select(Competence, func.count(CompetenceEvidence.id).label("evidence_count"))
        .outerjoin(CompetenceEvidence, CompetenceEvidence.competence_id == Competence.id)
        .where(Competence.user_id == user.id)
        .group_by(Competence.id)
        .order_by(Competence.created_at.desc())
    ).all()
    result = []
    for competence, evidence_count in rows:
        item = CompetenceOut.model_validate(competence).model_dump()
        item["evidence_count"] = evidence_count or 0
        result.append(item)
    return result


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


@router.get("/competences/{competence_id}/evidence", response_model=list[CompetenceEvidenceOut])
def list_evidence(competence_id: int, db: Db, user: CurrentUser) -> list[CompetenceEvidence]:
    competence = db.get(Competence, competence_id)
    if not competence:
        raise HTTPException(status_code=404, detail="Competence not found")
    if competence.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return list(db.scalars(
        select(CompetenceEvidence).where(CompetenceEvidence.competence_id == competence_id)
        .order_by(CompetenceEvidence.created_at)
    ))


@router.post("/competences/{competence_id}/evidence", response_model=CompetenceEvidenceOut, status_code=status.HTTP_201_CREATED)
def record_evidence(competence_id: int, payload: CompetenceEvidenceCreate, db: Db, user: CurrentUser) -> CompetenceEvidence:
    """Record a practice fact as proof of a competence. The source is
    validated: only your own fulfilled commitments and only your own
    verified results count."""
    competence = db.get(Competence, competence_id)
    if not competence:
        raise HTTPException(status_code=404, detail="Competence not found")
    if competence.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if payload.source_type == "commitment_fulfilled":
        source = db.get(Commitment, payload.source_id)
        if not source or source.user_id != user.id:
            raise HTTPException(status_code=404, detail="Commitment not found")
        if source.status != "fulfilled":
            raise DomainError(
                409, INVALID_STATE_TRANSITION,
                "Only a fulfilled commitment can serve as competence evidence",
            )
    else:  # result_verified
        source = db.get(Result, payload.source_id)
        if not source or source.reported_by != user.id:
            raise HTTPException(status_code=404, detail="Result not found")
        if source.status not in ("verified", "partially_verified"):
            raise DomainError(
                409, INVALID_STATE_TRANSITION,
                "Only a verified result can serve as competence evidence",
            )

    evidence = CompetenceEvidence(
        user_id=user.id, competence_id=competence_id,
        source_type=payload.source_type, source_id=payload.source_id,
        note=payload.note,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence