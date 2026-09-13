"""Results, evidence and verification endpoints (Track C5).

Closes the loop the critique calls the most underdeveloped part of
CAOS: a completed task is not an achieved goal (INV-3), and a result is
not verified just because its reporter says so (INV-4).
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..errors import DomainError, RESULT_ALREADY_VERIFIED, SELF_VERIFICATION_FORBIDDEN
from ..permissions import require_capability
from ..deps import current_user
from ..models import AuditEvent, Evidence, GoalCriterion, GoalMeasurement, Notification, Result, User, Verification
from ..schemas import (
    EvidenceCreate, EvidenceOut, GoalCriterionCreate, GoalCriterionOut,
    GoalMeasurementCreate, GoalMeasurementOut, ResultCreate, ResultOut, ResultVerify,
)

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

_VERIFIABLE_STATUSES = {"reported", "under_verification", "disputed"}


# --- criteria & measurements ---


@router.get("/goals/{goal_id}/criteria", response_model=list[GoalCriterionOut])
def list_criteria(goal_id: int, db: Db, user: CurrentUser) -> list[GoalCriterion]:
    require_goal(db, user.id, goal_id)
    return list(db.scalars(
        select(GoalCriterion).where(GoalCriterion.goal_id == goal_id).order_by(GoalCriterion.created_at)
    ))


@router.post("/goals/{goal_id}/criteria", response_model=GoalCriterionOut, status_code=status.HTTP_201_CREATED)
def create_criterion(goal_id: int, payload: GoalCriterionCreate, db: Db, user: CurrentUser) -> GoalCriterion:
    require_goal(db, user.id, goal_id)
    criterion = GoalCriterion(goal_id=goal_id, **payload.model_dump())
    db.add(criterion)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="goal_criterion", entity_id=criterion.id,
        action="created", detail=criterion.name,
    ))
    db.commit()
    db.refresh(criterion)
    return criterion


@router.post("/criteria/{criterion_id}/measurements", response_model=GoalMeasurementOut, status_code=status.HTTP_201_CREATED)
def record_measurement(criterion_id: int, payload: GoalMeasurementCreate, db: Db, user: CurrentUser) -> GoalMeasurement:
    criterion = db.get(GoalCriterion, criterion_id)
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")
    require_goal(db, user.id, criterion.goal_id)

    measurement = GoalMeasurement(
        criterion_id=criterion_id, value=payload.value, source=payload.source, recorded_by=user.id
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


@router.get("/criteria/{criterion_id}/measurements", response_model=list[GoalMeasurementOut])
def list_measurements(criterion_id: int, db: Db, user: CurrentUser) -> list[GoalMeasurement]:
    """Criterion dynamics: baseline -> ... -> actual over time."""
    criterion = db.get(GoalCriterion, criterion_id)
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")
    require_goal(db, user.id, criterion.goal_id)
    return list(db.scalars(
        select(GoalMeasurement).where(GoalMeasurement.criterion_id == criterion_id)
        .order_by(GoalMeasurement.measured_at)
    ))


# --- results & evidence ---


@router.get("/goals/{goal_id}/results", response_model=list[ResultOut])
def list_results(goal_id: int, db: Db, user: CurrentUser) -> list[dict]:
    require_goal(db, user.id, goal_id)
    rows = db.execute(
        select(Result, func.count(Evidence.id).label("evidence_count"))
        .outerjoin(Evidence, Evidence.result_id == Result.id)
        .where(Result.goal_id == goal_id)
        .group_by(Result.id)
        .order_by(Result.created_at.desc())
    ).all()
    out = []
    for result, evidence_count in rows:
        item = ResultOut.model_validate(result).model_dump()
        item["evidence_count"] = evidence_count or 0
        out.append(item)
    return out


@router.post("/goals/{goal_id}/results", response_model=ResultOut, status_code=status.HTTP_201_CREATED)
def report_result(goal_id: int, payload: ResultCreate, db: Db, user: CurrentUser) -> Result:
    require_goal(db, user.id, goal_id)
    if payload.task_id is not None and not _task_exists(db, payload.task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    result = Result(goal_id=goal_id, reported_by=user.id, **payload.model_dump())
    db.add(result)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="result", entity_id=result.id,
        action="reported", detail=result.description[:100],
    ))
    db.commit()
    db.refresh(result)
    return result


def _task_exists(db: Session, task_id: int) -> bool:
    from ..models import Task

    return db.get(Task, task_id) is not None


@router.post("/results/{result_id}/evidence", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def attach_evidence(result_id: int, payload: EvidenceCreate, db: Db, user: CurrentUser) -> Evidence:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    require_goal(db, user.id, result.goal_id)

    evidence = Evidence(result_id=result_id, created_by=user.id, **payload.model_dump())
    db.add(evidence)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="evidence", entity_id=evidence.id,
        action="attached", detail=payload.evidence_type,
    ))
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/results/{result_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(result_id: int, db: Db, user: CurrentUser) -> list[Evidence]:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    require_goal(db, user.id, result.goal_id)
    return list(db.scalars(
        select(Evidence).where(Evidence.result_id == result_id).order_by(Evidence.created_at)
    ))


# --- verification (INV-4) ---


@router.post("/results/{result_id}/verify", response_model=ResultOut)
def verify_result(result_id: int, payload: ResultVerify, db: Db, user: CurrentUser) -> Result:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    goal = require_goal(db, user.id, result.goal_id)
    require_capability(db, user, goal, "verify_result")

    if result.reported_by == user.id:
        raise DomainError(
            403, SELF_VERIFICATION_FORBIDDEN,
            "The reporter of a result cannot verify it - another participant must verify",
        )
    if result.status not in _VERIFIABLE_STATUSES:
        raise DomainError(
            409, RESULT_ALREADY_VERIFIED,
            f"Result in status '{result.status}' cannot be verified again",
        )

    verification = Verification(
        result_id=result_id, verifier_id=user.id,
        status=payload.status, rationale=payload.rationale,
    )
    result.status = payload.status
    result.verified_at = datetime.now(UTC) if payload.status in ("verified", "partially_verified") else None
    db.add(verification)
    db.add(AuditEvent(
        actor_id=user.id, entity_type="result", entity_id=result_id,
        action=f"verification:{payload.status}", detail=payload.rationale[:100],
    ))
    db.add(Notification(
        user_id=result.reported_by, entity_type="result", entity_id=result_id,
        message=f"Your result '{result.description[:60]}' is now {payload.status}",
    ))
    db.commit()
    db.refresh(result)
    return result
