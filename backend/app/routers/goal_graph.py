"""Typed goal graph endpoints (ADR-0002, Track C1).

The graph answers operational questions a tree cannot: what depends on
this goal, what supports it, what conflicts with it — and what stops if
it fails.
"""

from collections import deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal
from ..permissions import require_capability
from ..db import get_db
from ..deps import current_user
from ..models import Activity, AuditEvent, Commitment, Decision, Goal, GoalRelation, Problem, Project, ProjectGoal, Result, Task, User
from ..schemas import ExplainNode, GoalExplain, GoalImpact, GoalRelationCreate, GoalRelationOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

# Edge types where a cycle is meaningless and therefore forbidden.
_HIERARCHICAL_TYPES = {"concretizes", "depends_on", "blocks", "supersedes"}


def _would_create_cycle(db: Session, source_id: int, target_id: int, relation_type: str) -> bool:
    """True if adding source->target closes a loop of same-type edges.

    Cycles are only meaningless for ordering relations (concretizes,
    depends_on, blocks, supersedes); supports/conflicts/contributes may
    legitimately form loops.
    """
    if relation_type not in _HIERARCHICAL_TYPES:
        return False
    edges = db.execute(
        select(GoalRelation.source_goal_id, GoalRelation.target_goal_id)
        .where(GoalRelation.relation_type == relation_type)
    ).all()
    adjacency: dict[int, list[int]] = {}
    for src, dst in edges:
        adjacency.setdefault(src, []).append(dst)
    # A cycle appears if target already reaches source.
    queue: deque[int] = deque([target_id])
    seen = {target_id}
    while queue:
        node = queue.popleft()
        if node == source_id:
            return True
        for neighbour in adjacency.get(node, []):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return False


@router.get("/goals/{goal_id}/relations", response_model=list[GoalRelationOut])
def list_goal_relations(goal_id: int, db: Db, user: CurrentUser) -> list[GoalRelation]:
    require_goal(db, user.id, goal_id)
    return list(db.scalars(
        select(GoalRelation).where(
            (GoalRelation.source_goal_id == goal_id) | (GoalRelation.target_goal_id == goal_id)
        ).order_by(GoalRelation.created_at.desc())
    ))


@router.post("/goals/{goal_id}/relations", response_model=GoalRelationOut, status_code=status.HTTP_201_CREATED)
def create_goal_relation(goal_id: int, payload: GoalRelationCreate, db: Db, user: CurrentUser) -> GoalRelation:
    goal = require_goal(db, user.id, goal_id)  # source
    require_capability(db, user, goal, "create_relation")
    require_goal(db, user.id, payload.target_goal_id)  # target

    if goal_id == payload.target_goal_id:
        raise HTTPException(status_code=400, detail="A goal cannot relate to itself")

    duplicate = db.scalar(
        select(GoalRelation).where(
            GoalRelation.source_goal_id == goal_id,
            GoalRelation.target_goal_id == payload.target_goal_id,
            GoalRelation.relation_type == payload.relation_type,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="This relation already exists")

    if _would_create_cycle(db, goal_id, payload.target_goal_id, payload.relation_type):
        raise HTTPException(status_code=400, detail="Forbidden: this relation would create a cycle")

    relation = GoalRelation(
        source_goal_id=goal_id,
        target_goal_id=payload.target_goal_id,
        relation_type=payload.relation_type,
        rationale=payload.rationale,
        author_id=user.id,
    )
    db.add(relation)
    db.flush()
    db.add(AuditEvent(
        actor_id=user.id, entity_type="goal_relation", entity_id=relation.id,
        action="created", detail=f"{payload.relation_type}: {goal_id}->{payload.target_goal_id}",
    ))
    db.commit()
    db.refresh(relation)
    return relation


@router.get("/goals/{goal_id}/impact", response_model=GoalImpact)
def goal_impact(goal_id: int, db: Db, user: CurrentUser) -> GoalImpact:
    """What depends on / supports / conflicts with this goal."""
    require_goal(db, user.id, goal_id)

    relations = list(db.scalars(
        select(GoalRelation).where(
            (GoalRelation.source_goal_id == goal_id) | (GoalRelation.target_goal_id == goal_id)
        )
    ))

    dependents = {r.source_goal_id for r in relations if r.target_goal_id == goal_id and r.relation_type == "depends_on"}
    # Transitive closure over depends_on edges: everything that reaches
    # this goal through a chain, minus the direct dependents.
    all_depends = db.execute(
        select(GoalRelation.source_goal_id, GoalRelation.target_goal_id)
        .where(GoalRelation.relation_type == "depends_on")
    ).all()
    reverse_adjacency: dict[int, list[int]] = {}
    for src, dst in all_depends:
        reverse_adjacency.setdefault(dst, []).append(src)
    reachable = set()
    queue: deque[int] = deque([goal_id])
    while queue:
        node = queue.popleft()
        for dependent in reverse_adjacency.get(node, []):
            if dependent not in reachable and dependent != goal_id:
                reachable.add(dependent)
                queue.append(dependent)
    transitive = reachable - dependents

    return GoalImpact(
        goal_id=goal_id,
        direct_dependents=len(dependents),
        transitive_dependents=len(transitive),
        supporters=sum(1 for r in relations if r.target_goal_id == goal_id and r.relation_type in ("supports", "contributes_to")),
        conflicts=sum(1 for r in relations if r.relation_type == "conflicts_with" and goal_id in (r.source_goal_id, r.target_goal_id)),
        sub_goals=len(list(db.scalars(select(Goal.id).where(Goal.parent_goal_id == goal_id)))),
        projects=len(list(db.scalars(select(Project.id).where(Project.goal_id == goal_id)))),
        decisions=len(list(db.scalars(select(Decision.id).where(Decision.goal_id == goal_id)))),
    )


@router.get("/goals/{goal_id}/explain", response_model=GoalExplain)
def explain_goal(goal_id: int, db: Db, user: CurrentUser) -> GoalExplain:
    """The justification chain of a goal: problem -> goal -> decisions ->
    commitments -> tasks -> results (Track F, critique sections 77/89).

    Answers 'why does this exist?' with facts from the domain graph
    instead of a chat-bot reconstruction.
    """
    goal = require_goal(db, user.id, goal_id)

    chain: list[ExplainNode] = []
    if goal.problem_id:
        problem = db.get(Problem, goal.problem_id)
        if problem:
            chain.append(ExplainNode(kind="problem", id=problem.id, title=problem.title, status=problem.status, detail=problem.description[:200]))
    if goal.parent_goal_id:
        parent = db.get(Goal, goal.parent_goal_id)
        if parent:
            chain.append(ExplainNode(kind="goal", id=parent.id, title=parent.title, status=parent.status, detail="родительская цель"))

    decisions = list(db.scalars(select(Decision).where(Decision.goal_id == goal_id).order_by(Decision.created_at)))
    for d in decisions:
        chain.append(ExplainNode(kind="decision", id=d.id, title=d.title, status=d.status, detail=d.proposal[:200]))

    commitments = list(db.scalars(select(Commitment).where(Commitment.goal_id == goal_id).order_by(Commitment.created_at)))
    commitment_ids = [c.id for c in commitments]
    for c in commitments:
        chain.append(ExplainNode(kind="commitment", id=c.id, title=c.description[:120], status=c.status, detail=c.expected_result[:200]))

    tasks: list[Task] = []
    if commitment_ids:
        tasks = list(db.scalars(select(Task).where(Task.commitment_id.in_(commitment_ids)).order_by(Task.created_at)))
    project_ids = set(db.scalars(select(Project.id).where(Project.goal_id == goal_id)))
    project_ids |= set(db.scalars(select(ProjectGoal.project_id).where(ProjectGoal.goal_id == goal_id)))
    if project_ids:
        tasks = list(db.scalars(select(Task).where(Task.project_id.in_(project_ids)).order_by(Task.created_at)))
    for t in tasks:
        chain.append(ExplainNode(kind="task", id=t.id, title=t.title, status=t.status))

    activities = list(db.scalars(select(Activity).where(Activity.goal_id == goal_id).order_by(Activity.created_at)))
    for a in activities:
        chain.append(ExplainNode(kind="activity", id=a.id, title=a.title[:120], status=a.status, detail=f"тип: {a.activity_type}"))

    results = list(db.scalars(select(Result).where(Result.goal_id == goal_id).order_by(Result.created_at)))
    for r in results:
        chain.append(ExplainNode(kind="result", id=r.id, title=r.description[:120], status=r.status, detail=r.actual_state[:200]))

    counts = {
        "decisions": len(decisions),
        "commitments": len(commitments),
        "tasks": len(tasks),
        "activities": len(activities),
        "results": len(results),
    }
    return GoalExplain(goal_id=goal_id, chain=chain, counts=counts)
