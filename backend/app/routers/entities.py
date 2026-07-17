from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import AuditEvent, Decision, DecisionEvent, Goal, KnowledgeItem, Notification, Problem, Project, ProjectMember, Task, Team, TeamMember, User, Vote
from ..schemas import AuditEventOut, DecisionCreate, DecisionEventCreate, DecisionEventOut, DecisionOut, GoalCreate, GoalOut, MemberCreate, MemberOut, ProblemCreate, ProblemOut, ProjectCreate, ProjectMemberOut, ProjectOut, ProjectStatusUpdate, TaskAssign, TaskCreate, TaskOut, TeamCreate, TeamOut, VoteCreate, VoteOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
T = TypeVar("T")


def _user_project_ids(db: Session, user_id: int) -> set[int]:
    """Return set of project IDs the user owns or is a member of."""
    owned = set(db.scalars(select(Project.id).where(Project.owner_id == user_id)))
    member = set(db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    ))
    return owned | member


def _user_goal_ids(db: Session, user_id: int) -> set[int]:
    """Return set of goal IDs owned by user or linked to user's projects."""
    owned = set(db.scalars(select(Goal.id).where(Goal.owner_id == user_id)))
    project_goal_ids = set(db.scalars(
        select(Project.goal_id).where(Project.owner_id == user_id, Project.goal_id.isnot(None))
    ))
    member_goal_ids = set(db.scalars(
        select(Project.goal_id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id, Project.goal_id.isnot(None))
    ))
    return owned | project_goal_ids | member_goal_ids


@router.get("/problems", response_model=list[ProblemOut])
def list_problems(db: Db, user: CurrentUser, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)) -> list[Problem]:
    return list(db.scalars(
        select(Problem)
        .where(Problem.author_id == user.id)
        .order_by(Problem.created_at.desc())
        .offset(skip)
        .limit(limit)
    ))


@router.post("/problems", response_model=ProblemOut, status_code=status.HTTP_201_CREATED)
def create_problem(payload: ProblemCreate, db: Db, user: CurrentUser) -> Problem:
    item = Problem(**payload.model_dump(), author_id=user.id)
    db.add(item)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, entity_type="problem", entity_id=item.id, action="created", detail=item.title))
    db.commit()
    db.refresh(item)
    return item


@router.get("/goals", response_model=list[GoalOut])
def list_goals(db: Db, user: CurrentUser) -> list[Goal]:
    goal_ids = _user_goal_ids(db, user.id)
    if not goal_ids:
        return []
    return list(db.scalars(
        select(Goal)
        .where(Goal.id.in_(goal_ids))
        .order_by(Goal.created_at.desc())
    ))


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, db: Db, user: CurrentUser) -> Goal:
    if payload.problem_id and not db.get(Problem, payload.problem_id):
        raise HTTPException(status_code=404, detail="Problem not found")
    if payload.parent_goal_id and not db.get(Goal, payload.parent_goal_id):
        raise HTTPException(status_code=404, detail="Parent goal not found")
    item = Goal(**payload.model_dump(), owner_id=user.id)
    db.add(item)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, entity_type="goal", entity_id=item.id, action="created", detail=item.title))
    db.commit()
    db.refresh(item)
    return item


@router.get("/goals/{goal_id}/sub-goals", response_model=list[GoalOut])
def list_sub_goals(goal_id: int, db: Db, user: CurrentUser) -> list[Goal]:
    goal_ids = _user_goal_ids(db, user.id)
    if goal_id not in goal_ids:
        raise HTTPException(status_code=403, detail="Goal access denied")
    return list(db.scalars(select(Goal).where(Goal.parent_goal_id == goal_id).order_by(Goal.created_at.desc())))


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(db: Db, user: CurrentUser) -> list[Decision]:
    return list(db.scalars(select(Decision).where(Decision.author_id == user.id).order_by(Decision.created_at.desc())))


@router.post("/decisions", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate, db: Db, user: CurrentUser) -> Decision:
    if payload.goal_id and not db.get(Goal, payload.goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    decision = Decision(**payload.model_dump(), author_id=user.id)
    db.add(decision)
    db.flush()
    db.add(DecisionEvent(decision_id=decision.id, author_id=user.id, event_type="proposal", content=payload.proposal))
    db.commit()
    db.refresh(decision)
    return decision


@router.get("/decisions/{decision_id}/events", response_model=list[DecisionEventOut])
def list_decision_events(decision_id: int, db: Db, user: CurrentUser) -> list[DecisionEvent]:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.author_id != user.id:
        raise HTTPException(status_code=403, detail="Decision access denied")
    return list(db.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == decision_id).order_by(DecisionEvent.created_at)))


@router.post("/decisions/{decision_id}/events", response_model=DecisionEventOut, status_code=status.HTTP_201_CREATED)
def add_decision_event(decision_id: int, payload: DecisionEventCreate, db: Db, user: CurrentUser) -> DecisionEvent:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the decision author can add events")
    event = DecisionEvent(decision_id=decision_id, author_id=user.id, **payload.model_dump())
    db.add(event)
    if payload.event_type in {"accepted", "rejected", "revised"}:
        decision.status = payload.event_type
    db.add(AuditEvent(actor_id=user.id, entity_type="decision", entity_id=decision_id, action=payload.event_type, detail=decision.title))
    db.add(Notification(user_id=user.id, entity_type="decision", entity_id=decision_id, message=f"Decision '{decision.title}' {payload.event_type}"))
    db.commit()
    db.refresh(event)
    return event


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Db, user: CurrentUser) -> list[dict]:
    project_ids = _user_project_ids(db, user.id)
    if not project_ids:
        return []
    rows = db.execute(
        select(Project, func.count(KnowledgeItem.id).label("knowledge_count"))
        .outerjoin(KnowledgeItem, KnowledgeItem.project_id == Project.id)
        .where(Project.id.in_(project_ids))
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    ).all()
    result = []
    for project, kcount in rows:
        d = {c.name: getattr(project, c.name) for c in Project.__table__.columns}
        d["knowledge_count"] = kcount or 0
        result.append(d)
    return result


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Db, user: CurrentUser) -> Project:
    if payload.goal_id and not db.get(Goal, payload.goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    item = Project(**payload.model_dump(), owner_id=user.id)
    db.add(item)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, entity_type="project", entity_id=item.id, action="created", detail=item.title))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/projects/{project_id}/status", response_model=ProjectOut)
def update_project_status(project_id: int, payload: ProjectStatusUpdate, db: Db, user: CurrentUser) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can change status")
    valid = {"planned", "active", "completed", "on_hold"}
    if payload.status not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status. Valid: {valid}")
    project.status = payload.status
    db.add(AuditEvent(actor_id=user.id, entity_type="project", entity_id=project_id, action=payload.status, detail=project.title))
    db.add(Notification(user_id=user.id, entity_type="project", entity_id=project_id, message=f"Project '{project.title}' status changed to {payload.status}"))
    db.commit()
    db.refresh(project)
    return project


@router.get("/teams", response_model=list[TeamOut])
def list_teams(db: Db, user: CurrentUser) -> list[Team]:
    query = select(Team).join(TeamMember, TeamMember.team_id == Team.id).where(TeamMember.user_id == user.id).order_by(Team.created_at.desc())
    return list(db.scalars(query))


@router.post("/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, db: Db, user: CurrentUser) -> Team:
    team = Team(**payload.model_dump(), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(team)
    return team


@router.get("/teams/{team_id}/members", response_model=list[MemberOut])
def list_team_members(team_id: int, db: Db, user: CurrentUser) -> list[TeamMember]:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if not db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Team membership required")
    return list(db.scalars(select(TeamMember).where(TeamMember.team_id == team_id).order_by(TeamMember.created_at)))


@router.post("/teams/{team_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_team_member(team_id: int, payload: MemberCreate, db: Db, user: CurrentUser) -> TeamMember:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can add members")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id)):
        raise HTTPException(status_code=409, detail="User is already a team member")
    member = TeamMember(team_id=team_id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_project_member(project_id: int, payload: MemberCreate, db: Db, user: CurrentUser) -> ProjectMember:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can add members")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id)):
        raise HTTPException(status_code=409, detail="User is already a project member")
    member = ProjectMember(project_id=project_id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members(project_id: int, db: Db, user: CurrentUser) -> list[ProjectMember]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and not db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Project membership required")
    return list(db.scalars(select(ProjectMember).where(ProjectMember.project_id == project_id).order_by(ProjectMember.created_at)))


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: int, db: Db, user: CurrentUser) -> list[dict]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and not db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Project membership required")
    rows = db.execute(
        select(Task, User.display_name)
        .outerjoin(User, User.id == Task.assignee_id)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at)
    ).all()
    result = []
    for task, assignee_name in rows:
        d = {c.name: getattr(task, c.name) for c in Task.__table__.columns}
        d["assignee_name"] = assignee_name
        result.append(d)
    return result


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(project_id: int, payload: TaskCreate, db: Db, user: CurrentUser) -> Task:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and not db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Project membership required")
    item = Task(**payload.model_dump(), project_id=project_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Db, user: CurrentUser) -> Task:
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    if item.project.owner_id != user.id and not db.scalar(select(ProjectMember).where(ProjectMember.project_id == item.project_id, ProjectMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Project membership required")
    item.status = "done"
    db.add(AuditEvent(actor_id=user.id, entity_type="task", entity_id=task_id, action="completed", detail=item.title))
    db.add(Notification(user_id=user.id, entity_type="task", entity_id=task_id, message=f"Task '{item.title}' completed"))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/tasks/{task_id}/assign", response_model=TaskOut)
def assign_task(task_id: int, payload: TaskAssign, db: Db, user: CurrentUser) -> Task:
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    if item.project.owner_id != user.id and not db.scalar(select(ProjectMember).where(ProjectMember.project_id == item.project_id, ProjectMember.user_id == user.id)):
        raise HTTPException(status_code=403, detail="Project membership required")
    if payload.assignee_id is not None:
        assignee = db.get(User, payload.assignee_id)
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee user not found")
    item.assignee_id = payload.assignee_id
    db.add(AuditEvent(actor_id=user.id, entity_type="task", entity_id=task_id, action="assigned", detail=item.title))
    if payload.assignee_id is not None:
        db.add(Notification(user_id=payload.assignee_id, entity_type="task", entity_id=task_id, message=f"Task '{item.title}' assigned to you"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/audit", response_model=list[AuditEventOut])
def list_audit_events(db: Db, user: CurrentUser, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)) -> list[AuditEvent]:
    return list(db.scalars(
        select(AuditEvent)
        .where(AuditEvent.actor_id == user.id)
        .order_by(AuditEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
    ))


@router.post("/decisions/{decision_id}/vote", response_model=VoteOut, status_code=status.HTTP_201_CREATED)
def cast_vote(decision_id: int, payload: VoteCreate, db: Db, user: CurrentUser) -> Vote:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.status not in ("proposed", "in_discussion", "voting"):
        raise HTTPException(status_code=400, detail="Decision is not open for voting")
    existing = db.scalar(select(Vote).where(Vote.decision_id == decision_id, Vote.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Already voted")
    vote = Vote(decision_id=decision_id, user_id=user.id, variant=payload.variant, comment=payload.comment)
    db.add(vote)
    db.add(AuditEvent(actor_id=user.id, entity_type="decision", entity_id=decision_id, action="vote", detail=payload.variant))
    db.commit()
    db.refresh(vote)
    return vote


@router.get("/decisions/{decision_id}/votes", response_model=list[VoteOut])
def list_votes(decision_id: int, db: Db, user: CurrentUser) -> list[Vote]:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only decision author can view votes")
    return list(db.scalars(select(Vote).where(Vote.decision_id == decision_id).order_by(Vote.created_at.desc())))


@router.post("/decisions/{decision_id}/finalize", response_model=DecisionOut)
def finalize_decision(decision_id: int, db: Db, user: CurrentUser) -> Decision:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only decision author can finalize")
    votes = list(db.scalars(select(Vote).where(Vote.decision_id == decision_id)))
    if len(votes) < decision.quorum:
        raise HTTPException(status_code=400, detail=f"Quorum not met: {len(votes)}/{decision.quorum}")
    accept_count = sum(1 for v in votes if v.variant == "accept")
    reject_count = sum(1 for v in votes if v.variant == "reject")
    if accept_count > reject_count:
        decision.status = "accepted"
    else:
        decision.status = "rejected"
    db.add(AuditEvent(actor_id=user.id, entity_type="decision", entity_id=decision_id, action="finalized", detail=decision.status))
    db.add(Notification(user_id=decision.author_id, entity_type="decision", entity_id=decision_id, message=f"Decision '{decision.title}' {decision.status}"))
    db.commit()
    db.refresh(decision)
    return decision
