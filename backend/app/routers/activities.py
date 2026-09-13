"""Activities and evaluations endpoints (Track D).

Activities are forms of work beyond tasks (meeting, research,
discussion...) always tied to a goal. Evaluations record what a
verified result MEANS for the goal and what was learned.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..errors import DomainError, FORBIDDEN_SCOPE, INVALID_STATE_TRANSITION
from ..models import Activity, AuditEvent, Evaluation, Result, User
from ..schemas import ActivityCreate, ActivityStatusUpdate, EvaluationCreate, EvaluationOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

ACTIVITY_TYPES = {"task", "meeting", "research", "discussion", "decision", "external_action"}
ACTIVITY_TRANSITIONS = {
    "planned": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
}
EVALUATION_CONCLUSIONS = {
    "successful", "partially_successful", "unsuccessful",
    "decision_correct_implementation_failed", "decision_flawed", "external_factors",
}


def _out(a: Activity, creator_name: str) -> dict:
    return {
        "id": a.id,
        "goal_id": a.goal_id,
        "commitment_id": a.commitment_id,
        "activity_type": a.activity_type,
        "title": a.title,
        "description": a.description,
        "status": a.status,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "created_by": a.created_by,
        "creator_name": creator_name,
        "created_at": a.created_at.isoformat(),
    }


@router.get("/goals/{goal_id}/activities")
def list_activities(goal_id: int, db: Db, user: CurrentUser) -> list[dict]:
    from ..models import UserProfile

    require_goal(db, user.id, goal_id)
    rows = db.execute(
        select(Activity, func.coalesce(UserProfile.display_name, ""))
        .outerjoin(UserProfile, UserProfile.user_id == Activity.created_by)
        .where(Activity.goal_id == goal_id)
        .order_by(Activity.created_at.desc())
    ).all()
    return [_out(a, name) for a, name in rows]


@router.post("/goals/{goal_id}/activities", status_code=status.HTTP_201_CREATED)
def create_activity(goal_id: int, payload: ActivityCreate, db: Db, user: CurrentUser) -> dict:
    from ..models import Commitment

    require_goal(db, user.id, goal_id)
    if payload.activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=422, detail=f"activity_type must be one of {sorted(ACTIVITY_TYPES)}")
    if payload.commitment_id is not None:
        commitment = db.get(Commitment, payload.commitment_id)
        if not commitment or commitment.goal_id != goal_id:
            raise HTTPException(status_code=404, detail="Commitment not found in this goal")

    activity = Activity(goal_id=goal_id, created_by=user.id, **payload.model_dump())
    db.add(activity)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="activity", entity_id=activity.id,
        action="created", detail=f"{payload.activity_type}: {payload.title[:80]}",
    ))
    db.commit()
    return _out(activity, user.display_name)


@router.post("/activities/{activity_id}/status")
def update_activity_status(activity_id: int, payload: ActivityStatusUpdate, db: Db, user: CurrentUser) -> dict:
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    goal_owner = db.scalar(
        select(Activity.goal_id).where(Activity.id == activity_id)
    )
    require_goal(db, user.id, goal_owner)
    if activity.created_by != user.id and payload.status != "cancelled":
        # only the creator drives their activity; anyone with goal access
        # may cancel it if the creator disappeared
        raise DomainError(403, FORBIDDEN_SCOPE, "Only the creator can drive this activity")

    allowed = ACTIVITY_TRANSITIONS.get(activity.status, set())
    if payload.status not in allowed:
        raise DomainError(
            409, INVALID_STATE_TRANSITION,
            f"Cannot move activity from '{activity.status}' to '{payload.status}'. Allowed: {sorted(allowed)}",
        )
    activity.status = payload.status
    now = datetime.now(UTC)
    if payload.status == "in_progress":
        activity.started_at = now
    elif payload.status == "completed":
        activity.completed_at = now
    db.add(AuditEvent(
        actor_id=user.id, entity_type="activity", entity_id=activity_id,
        action=payload.status, detail=activity.title[:100],
    ))
    db.commit()
    return {"id": activity.id, "status": activity.status}


@router.get("/results/{result_id}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(result_id: int, db: Db, user: CurrentUser) -> list[Evaluation]:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    require_goal(db, user.id, result.goal_id)
    return list(db.scalars(
        select(Evaluation).where(Evaluation.result_id == result_id).order_by(Evaluation.created_at)
    ))


@router.post("/results/{result_id}/evaluations", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def create_evaluation(result_id: int, payload: EvaluationCreate, db: Db, user: CurrentUser) -> Evaluation:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    require_goal(db, user.id, result.goal_id)
    if payload.conclusion not in EVALUATION_CONCLUSIONS:
        raise HTTPException(status_code=422, detail=f"conclusion must be one of {sorted(EVALUATION_CONCLUSIONS)}")

    evaluation = Evaluation(result_id=result_id, evaluator_id=user.id, **payload.model_dump())
    db.add(evaluation)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="evaluation", entity_id=evaluation.id,
        action=payload.conclusion, detail=payload.insight[:100],
    ))
    db.commit()
    db.refresh(evaluation)
    return evaluation
