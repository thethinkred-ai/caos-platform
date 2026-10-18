"""Goal export to Markdown (external comment 03.10.2026, point 2).

Methodology may live outside the system: the whole goal workspace -
goal, criteria, resources, relations, participants, commitments,
activities, decisions, results with evidence and evaluations,
challenges, timeline - exports as one portable document."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from ..access import require_goal
from ..db import get_db
from ..deps import current_user
from ..models import (
    Activity, Challenge, Commitment, Decision, Evidence, Evaluation, Goal,
    GoalCriterion, GoalMeasurement, GoalParticipation, GoalRelation, Resource,
    Result, User, UserProfile, Verification,
)
from ..ru import GOAL_STATUS, ru

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


def _names(db: Session) -> dict[int, str]:
    participant = aliased(UserProfile)
    rows = db.execute(select(User.id, participant.display_name).outerjoin(participant, participant.user_id == User.id)).all()
    return {uid: (name or f"#{uid}") for uid, name in rows}


@router.get("/goals/{goal_id}/export")
def export_goal(goal_id: int, db: Db, user: CurrentUser) -> Response:
    goal = require_goal(db, user.id, goal_id)
    names = _names(db)
    lines: list[str] = [f"# {goal.title}", ""]

    if goal.description:
        lines += [goal.description, ""]
    lines.append(f"**Статус:** {ru(GOAL_STATUS, goal.status)} · №{goal.id}"
                 + (f" · срок до {goal.deadline:%d.%m.%Y}" if goal.deadline else ""))
    lines.append("")

    criteria = list(db.scalars(select(GoalCriterion).where(GoalCriterion.goal_id == goal_id).order_by(GoalCriterion.created_at)))
    if criteria:
        lines.append("## Критерии достижения")
        for c in criteria:
            measure = " → ".join(m.value for m in db.scalars(
                select(GoalMeasurement).where(GoalMeasurement.criterion_id == c.id).order_by(GoalMeasurement.measured_at)
            ))
            target = f"{c.baseline or '—'} → {c.target_value} {c.unit}".strip()
            lines.append(f"- **{c.name}** ({c.criterion_type}): {target}" + (f"; динамика: {measure}" if measure else ""))
        lines.append("")

    resources_list = list(db.scalars(select(Resource).where(Resource.goal_id == goal_id).order_by(Resource.created_at)))
    if resources_list:
        lines.append("## Ресурсы")
        for r in resources_list:
            mark = " ⚠️ критический" if r.is_critical else ""
            qty = f": {r.quantity} {r.unit}".rstrip() if r.quantity else ""
            lines.append(f"- {r.name}{qty} — {r.status}{mark}")
        lines.append("")

    relations = list(db.scalars(
        select(GoalRelation).where((GoalRelation.source_goal_id == goal_id) | (GoalRelation.target_goal_id == goal_id))
    ))
    if relations:
        lines.append("## Связи с другими целями")
        for rel in relations:
            direction = "→" if rel.source_goal_id == goal_id else "←"
            other = rel.target_goal_id if rel.source_goal_id == goal_id else rel.source_goal_id
            other_goal = db.get(Goal, other)
            other_title = other_goal.title if other_goal else f"№{other}"
            lines.append(f"- {direction} **{rel.relation_type}** «{other_title}»: {rel.rationale}")
        lines.append("")

    parts = list(db.scalars(select(GoalParticipation).where(GoalParticipation.goal_id == goal_id)))
    if parts:
        lines.append("## Участники")
        for p in parts:
            state = "участвует" if p.status == "active" else "вышел"
            lines.append(f"- {names.get(p.user_id, f'#{p.user_id}')} — {p.role} ({state})")
        lines.append("")

    commitments = list(db.scalars(select(Commitment).where(Commitment.goal_id == goal_id).order_by(Commitment.created_at)))
    if commitments:
        lines.append("## Обязательства")
        for c in commitments:
            lines.append(f"- **{names.get(c.user_id, f'#{c.user_id}')}**: {c.description} — {c.status}"
                         + (f" (до {c.deadline:%d.%m.%Y})" if c.deadline else ""))
        lines.append("")

    activities = list(db.scalars(select(Activity).where(Activity.goal_id == goal_id).order_by(Activity.created_at)))
    if activities:
        lines.append("## Деятельность")
        for a in activities:
            lines.append(f"- [{a.activity_type}] {a.title} — {a.status}")
        lines.append("")

    decisions = list(db.scalars(select(Decision).where(Decision.goal_id == goal_id).order_by(Decision.created_at)))
    if decisions:
        lines.append("## Решения")
        for d in decisions:
            lines.append(f"- **{d.title}** — {d.status} (метод: {d.decision_method})")
            lines.append(f"  - Предложение: {d.proposal[:300]}")
        lines.append("")

    results = list(db.scalars(select(Result).where(Result.goal_id == goal_id).order_by(Result.created_at)))
    if results:
        lines.append("## Результаты")
        for r in results:
            lines.append(f"- **{r.description}** — {r.status}")
            if r.actual_state:
                lines.append(f"  - Фактически: {r.actual_state}")
            for ev in db.scalars(select(Evidence).where(Evidence.result_id == r.id)):
                lines.append(f"  - Доказательство ({ev.evidence_type}): {ev.content[:200]}")
            for v in db.scalars(select(Verification).where(Verification.result_id == r.id)):
                lines.append(f"  - Проверка: {v.status} — {v.rationale[:200]} ({names.get(v.verifier_id, f'#{v.verifier_id}')})")
            for e in db.scalars(select(Evaluation).where(Evaluation.result_id == r.id)):
                lines.append(f"  - Оценка: {e.conclusion}. {e.insight[:200]}")
        lines.append("")

    challenges = list(db.scalars(
        select(Challenge).where(Challenge.target_type == "goal", Challenge.target_id == goal_id)
    ))
    if challenges:
        lines.append("## Возражения")
        for ch in challenges:
            lines.append(f"- **{ch.claim}** ({ch.status}): {ch.argument[:200]}")
            if ch.resolution:
                lines.append(f"  - Резолюция: {ch.resolution[:200]}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Экспортировано из CAOS {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. "
                 f"Живая цель: {goal.id}, статус «{ru(GOAL_STATUS, goal.status)}».*")

    markdown = "\n".join(lines)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="goal-{goal_id}.md"'},
    )
