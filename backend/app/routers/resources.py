"""Goal resources (external comment 03.10.2026): specialized labor, tools,
venues, funding - not every bottleneck is activity. Critical unsecured
resources are bottlenecks; securing them is a human action, recorded
here, never automatic allocation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Goal, Resource, User
from ..permissions import require_capability
from ..schemas import ResourceCreate, ResourceOut, ResourceUpdate

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/goals/{goal_id}/resources", response_model=list[ResourceOut])
def list_resources(goal_id: int, db: Db, user: CurrentUser) -> list[Resource]:
    require_goal(db, user.id, goal_id)
    return list(db.scalars(
        select(Resource).where(Resource.goal_id == goal_id).order_by(Resource.created_at)
    ))


@router.post("/goals/{goal_id}/resources", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(goal_id: int, payload: ResourceCreate, db: Db, user: CurrentUser) -> Resource:
    goal = require_goal(db, user.id, goal_id)
    require_capability(db, user, goal, "edit")
    resource = Resource(goal_id=goal_id, created_by=user.id, **payload.model_dump())
    db.add(resource)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="resource", entity_id=resource.id,
        action="created", detail=f"{payload.resource_type}: {payload.name[:80]}",
    ))
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, payload: ResourceUpdate, db: Db, user: CurrentUser) -> Resource:
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    goal = db.get(Goal, resource.goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_goal(db, user.id, resource.goal_id)
    require_capability(db, user, goal, "edit")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update")
    for field, value in updates.items():
        setattr(resource, field, value)
    db.add(AuditEvent(
        actor_id=user.id, entity_type="resource", entity_id=resource_id,
        action="updated", detail=", ".join(updates.keys()),
    ))
    db.commit()
    db.refresh(resource)
    return resource
