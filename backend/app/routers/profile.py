from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Competence, Decision, Goal, Problem, Project, ProjectMember, Task, TeamMember, User
from ..schemas import UserOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/profile/{user_id}")
def get_profile(user_id: int, db: Db, user: CurrentUser) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id != user.id:
        if target.profile_visibility == "private":
            raise HTTPException(status_code=403, detail="Profile is private")
        if target.profile_visibility == "members":
            shared_project = db.scalar(
                select(ProjectMember.project_id).where(ProjectMember.user_id == user.id).intersect(
                    select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
                )
            )
            shared_team = db.scalar(
                select(TeamMember.team_id).where(TeamMember.user_id == user.id).intersect(
                    select(TeamMember.team_id).where(TeamMember.user_id == user_id)
                )
            )
            if not shared_project and not shared_team:
                raise HTTPException(status_code=403, detail="Profile is members-only")

    problems = list(db.scalars(select(Problem).where(Problem.author_id == user_id).limit(50)))
    goals = list(db.scalars(select(Goal).where(Goal.owner_id == user_id).limit(50)))
    projects = list(db.scalars(select(Project).where(Project.owner_id == user_id).limit(50)))
    decisions = list(db.scalars(select(Decision).where(Decision.author_id == user_id).limit(50)))
    competences = list(db.scalars(
        select(Competence).where(Competence.user_id == user_id, Competence.is_visible == True)
    ))

    assigned_tasks = list(db.scalars(select(Task).where(Task.assignee_id == user_id, Task.status != "done").limit(20)))

    return {
        "user": UserOut.model_validate(target).model_dump(),
        "stats": {
            "problems": len(problems),
            "goals": len(goals),
            "projects": len(projects),
            "decisions": len(decisions),
            "open_tasks": len(assigned_tasks),
        },
        "competences": [{"name": c.name, "level": c.level, "description": c.description} for c in competences],
        "recent_activity": [
            {"type": "problem", "title": p.title, "status": p.status, "created_at": str(p.created_at)}
            for p in problems[:5]
        ] + [
            {"type": "goal", "title": g.title, "status": g.status, "created_at": str(g.created_at)}
            for g in goals[:5]
        ] + [
            {"type": "decision", "title": d.title, "status": d.status, "created_at": str(d.created_at)}
            for d in decisions[:5]
        ],
    }


@router.patch("/profile/visibility")
def update_visibility(
    db: Db, user: CurrentUser, visibility: str = "private"
) -> dict:
    if visibility not in ("private", "members", "public"):
        raise HTTPException(status_code=400, detail="Invalid visibility value")
    user.profile_visibility = visibility
    db.commit()
    return {"profile_visibility": visibility}


@router.patch("/profile/ai-consent")
def update_ai_consent(
    db: Db, user: CurrentUser, consent: bool = False
) -> dict:
    user.ai_consent = consent
    db.commit()
    return {"ai_consent": consent}
