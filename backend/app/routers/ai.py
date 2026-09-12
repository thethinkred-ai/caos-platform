from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import require_goal, user_goal_ids, user_project_ids
from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..llm import is_llm_available, llm_complete_sync
from ..models import AISuggestion, AuditEvent, Competence, Decision, DecisionEvent, Goal, KnowledgeItem, Problem, Project, ProjectMember, Task, User
from ..schemas import AIRecommendation, AISuggestionOut, AISuggestionResolve

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
settings = get_settings()


def _record_proposal(
    db: Session, user: User, endpoint: str, recommendation, target_type: str = "", target_id: int | None = None
):
    """Persist every AI output as a reviewable proposal (ADR-0003): the
    only channel through which AI can influence the domain."""
    snapshot = recommendation.suggestion[:2000]
    proposal = AISuggestion(
        user_id=user.id,
        endpoint=endpoint,
        suggestion=recommendation.suggestion,
        status="pending",
        model_name=recommendation.source,
        input_snapshot=snapshot,
        confidence=recommendation.confidence,
        proposal_type="recommendation",
        target_type=target_type,
        target_id=target_id,
    )
    db.add(proposal)
    db.commit()

SYSTEM_PROMPT = (
    "You are an AI assistant for a collaborative action platform (CAOS). "
    "Users formulate problems, set goals, run projects, and build a knowledge base. "
    "Respond concisely in Russian. Be specific and actionable."
)


def _require_own_problem(db: Session, user: User, problem_id: int) -> Problem:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if problem.author_id != user.id:
        raise HTTPException(status_code=403, detail="Problem access denied")
    return problem


def _stub_similar_problems(db: Session, user: User, problem_id: int) -> AIRecommendation:
    _require_own_problem(db, user, problem_id)
    others = list(db.scalars(
        select(Problem).where(Problem.author_id == user.id, Problem.id != problem_id).limit(5)
    ))
    titles = [p.title for p in others] or ["Похожих проблем не найдено"]
    return AIRecommendation(
        suggestion="Возможно, релевантные проблемы: " + "; ".join(titles),
        source="keyword-match",
        confidence=0.3,
    )


def _stub_similar_people(db: Session, user: User) -> AIRecommendation:
    return AIRecommendation(
        suggestion="AI-поиск участников будет подключён после выбора LLM-провайдера.",
        source="stub",
        confidence=0.0,
    )


def _visible_knowledge(db: Session, user: User, limit: int) -> list[KnowledgeItem]:
    from sqlalchemy import or_

    pids = user_project_ids(db, user.id)
    cond = KnowledgeItem.author_id == user.id
    if pids:
        cond = or_(cond, KnowledgeItem.project_id.in_(pids))
    return list(db.scalars(select(KnowledgeItem).where(cond).limit(limit)))


def _stub_find_knowledge(db: Session, user: User, query: str) -> AIRecommendation:
    items = _visible_knowledge(db, user, 5)
    if items:
        titles = [k.title for k in items]
        return AIRecommendation(
            suggestion=f"Найдено по ключевым словам: {'; '.join(titles)}",
            source="keyword-match",
            confidence=0.3,
        )
    return AIRecommendation(
        suggestion=f"AI-поиск знаний по запросу «{query}» — элементов в базе пока нет.",
        source="stub",
        confidence=0.0,
    )


def _stub_decompose_goal(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    return AIRecommendation(
        suggestion=f"Предлагается разбить цель «{goal.title}» на: 1) исследование, 2) планирование, 3) реализация, 4) оценка.",
        source="heuristic",
        confidence=0.2,
    )


def _llm_similar_problems(db: Session, user: User, problem_id: int) -> AIRecommendation:
    _require_own_problem(db, user, problem_id)
    others = list(db.scalars(
        select(Problem).where(Problem.author_id == user.id, Problem.id != problem_id).limit(10)
    ))
    context = f"Проблема: {problem.title}\nОписание: {problem.description}\n\nДругие проблемы:\n"
    context += "\n".join(f"- {p.title}: {p.description[:80]}" for p in others) or "Нет других проблем."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Найди 3 наиболее релевантные проблемы из списка ниже и объясни почему.\n{context}",
    )
    if not answer:
        return _stub_similar_problems(db, user, problem_id)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


def _llm_similar_people(db: Session, user: User) -> AIRecommendation:
    if not user.ai_consent:
        return AIRecommendation(suggestion="AI-анализ требует согласия на обработку данных. Включите AI-согласие в настройках профиля.", source="consent_required", confidence=0.0)
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Пользователь интересуется коллективной деятельностью. Подскажи, как найти единомышленников для совместной работы над проблемами и целями.",
    )
    if not answer:
        return _stub_similar_people(db, user)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)


def _llm_find_knowledge(db: Session, user: User, query: str) -> AIRecommendation:
    items = _visible_knowledge(db, user, 10)
    context = "\n".join(f"- {k.title}: {k.content[:100]}" for k in items) or "База знаний пуста."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Найди релевантные знания по запросу «{query}».\nДоступные элементы:\n{context}",
    )
    if not answer:
        return _stub_find_knowledge(db, user, query)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


def _llm_decompose_goal(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    projects = list(db.scalars(select(Project).where(Project.goal_id == goal_id).limit(5)))
    context = f"Цель: {goal.title}\nОписание: {goal.description}\n"
    if projects:
        context += "Существующие проекты:\n" + "\n".join(f"- {p.title} ({p.status})" for p in projects)
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Предложи декомпозицию цели на 3-5 подзадач с кратким обоснованием.\n{context}",
    )
    if not answer:
        return _stub_decompose_goal(db, user, goal_id)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


@router.get("/recommendations/similar-problems/{problem_id}", response_model=AIRecommendation)
def similar_problems(problem_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        result = _llm_similar_problems(db, user, problem_id)
    else:
        result = _stub_similar_problems(db, user, problem_id)
    _record_proposal(db, user, "similar_problems", result, "problem", problem_id)
    return result


@router.get("/recommendations/people", response_model=AIRecommendation)
def similar_people(db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        result = _llm_similar_people(db, user)
    else:
        result = _stub_similar_people(db, user)
    _record_proposal(db, user, "similar_people", result)
    return result


@router.get("/recommendations/knowledge", response_model=AIRecommendation)
def find_knowledge(db: Db, user: CurrentUser, q: str = Query(min_length=2, max_length=200)) -> AIRecommendation:
    if is_llm_available():
        result = _llm_find_knowledge(db, user, q)
    else:
        result = _stub_find_knowledge(db, user, q)
    _record_proposal(db, user, "find_knowledge", result)
    return result


@router.get("/recommendations/decompose/{goal_id}", response_model=AIRecommendation)
def decompose_goal(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        result = _llm_decompose_goal(db, user, goal_id)
    else:
        result = _stub_decompose_goal(db, user, goal_id)
    _record_proposal(db, user, "decompose_goal", result, "goal", goal_id)
    return result


def _llm_similar_goals(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    others = _other_visible_goals(db, user, goal_id)
    context = f"Цель: {goal.title}\nОписание: {goal.description}\n\nДругие цели:\n"
    context += "\n".join(f"- {g.title}: {g.description[:80]}" for g in others) or "Нет других целей."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Найди 3 наиболее близкие цели из списка ниже. Для каждой объясни, почему они совпадают или пересекаются, и предложи объединить усилия если это уместно.\n{context}",
    )
    if not answer:
        return AIRecommendation(suggestion="Похожие цели не найдены.", source="stub", confidence=0.0)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


def _llm_duplicate_goals(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    others = _other_visible_goals(db, user, goal_id)


def _other_visible_goals(db: Session, user: User, goal_id: int) -> list[Goal]:
    goal_ids = user_goal_ids(db, user.id) - {goal_id}
    if not goal_ids:
        return []
    return list(db.scalars(select(Goal).where(Goal.id.in_(goal_ids)).limit(10)))
    context = f"Цель: {goal.title}\nОписание: {goal.description}\n\nДругие цели:\n"
    context += "\n".join(f"- {g.title}: {g.description[:80]}" for g in others) or "Нет других целей."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Проанализируй, есть ли цели-дубликаты, которые преследуют тот же результат, но расходуют ресурсы независимо. Предложи координацию.\n{context}",
    )
    if not answer:
        return AIRecommendation(suggestion="Дубликатов не обнаружено.", source="stub", confidence=0.0)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)


def _llm_missing_competences(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    projects = list(db.scalars(select(Project).where(Project.goal_id == goal_id).limit(5)))
    participant_ids = {goal.owner_id} | {p.owner_id for p in projects}
    for proj in projects:
        participant_ids.update(db.scalars(
            select(ProjectMember.user_id).where(ProjectMember.project_id == proj.id)
        ))
    if participant_ids:
        all_comps = list(db.scalars(
            select(Competence).where(
                Competence.user_id.in_(participant_ids),
                Competence.is_visible.is_(True),
            ).limit(20)
        ))
    else:
        all_comps = []
    context = f"Цель: {goal.title}\nОписание: {goal.description}\n"
    if projects:
        context += "Проекты:\n" + "\n".join(f"- {p.title} ({p.status})" for p in projects)
    if all_comps:
        context += "\n\nДоступные компетенции участников:\n" + "\n".join(f"- {c.name} (уровень {c.level})" for c in all_comps)
    else:
        context += "\n\nКомпетенции участников пока не заполнены."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Проанализируя требования цели и доступные компетенции участников, определи, каких компетенций не хватает для достижения цели. Предложи, какие навыки нужно найти.\n{context}",
    )
    if not answer:
        return AIRecommendation(suggestion="Недостающие компетенции не определены.", source="stub", confidence=0.0)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)


def _llm_goal_context(db: Session, user: User, goal_id: int) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    projects = list(db.scalars(select(Project).where(Project.goal_id == goal_id).limit(5)))
    decisions = list(db.scalars(select(Decision).where(Decision.goal_id == goal_id).limit(5)))
    events = list(db.scalars(select(DecisionEvent).where(DecisionEvent.decision_id.in_([d.id for d in decisions])).limit(10)))
    audits = list(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "goal", AuditEvent.entity_id == goal_id).limit(10)))
    context = f"Цель: {goal.title}\nОписание: {goal.description}\nСтатус: {goal.status}\n"
    if projects:
        context += f"\nПроекты ({len(projects)}):\n" + "\n".join(f"- {p.title} ({p.status})" for p in projects)
    if decisions:
        context += f"\nРешения ({len(decisions)}):\n" + "\n".join(f"- {d.title} ({d.status})" for d in decisions)
    if events:
        context += f"\nСобытия решений ({len(events)}):\n" + "\n".join(f"- {e.event_type}: {e.content[:60]}" for e in events)
    if audits:
        context += f"\nЖурнал ({len(audits)}):\n" + "\n".join(f"- {a.action}: {a.detail}" for a in audits)
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Подготовь сжатый контекст для нового участника: как возникла цель, какие решения приняты, кто в чём участвует, какие варианты были отвергнуты. Объём — 3-5 предложений.\n{context}",
    )
    if not answer:
        return AIRecommendation(suggestion="Контекст недоступен.", source="stub", confidence=0.0)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


@router.get("/recommendations/similar-goals/{goal_id}", response_model=AIRecommendation)
def similar_goals(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_similar_goals(db, user, goal_id)
    return AIRecommendation(suggestion="AI-поиск совпадающих целей будет подключён после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/duplicate-goals/{goal_id}", response_model=AIRecommendation)
def duplicate_goals(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_duplicate_goals(db, user, goal_id)
    return AIRecommendation(suggestion="AI-поиск дубликатов будет подключён после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/missing-competences/{goal_id}", response_model=AIRecommendation)
def missing_competences(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_missing_competences(db, user, goal_id)
    return AIRecommendation(suggestion="AI-анализ компетенций будет подключён после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/goal-context/{goal_id}", response_model=AIRecommendation)
def goal_context(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_goal_context(db, user, goal_id)
    return AIRecommendation(suggestion="AI-восстановление контекста будет подключено после настройки LLM.", source="stub", confidence=0.0)


@router.get("/ai/status")
def ai_status(user: CurrentUser) -> dict:
    return {
        "llm_available": is_llm_available(),
        "model": settings.ai_model if is_llm_available() else None,
    }


@router.get("/tasks/{task_id}/match-people")
def match_people_to_task(task_id: int, db: Db, user: CurrentUser) -> list[dict]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = task.project
    if project.owner_id != user.id and not db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
    ):
        raise HTTPException(status_code=403, detail="Project membership required")
    requirements = task.competence_requirements or []
    if not requirements:
        return []
    member_ids = set(db.scalars(
        select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)
    )) | {project.owner_id}
    matches = []
    for uid in member_ids:
        comps = list(db.scalars(select(Competence).where(Competence.user_id == uid, Competence.is_visible == True)))
        matched = [c for c in comps if any(req.lower() in c.name.lower() for req in requirements)]
        if matched:
            u = db.get(User, uid)
            matches.append({
                "user_id": uid,
                "display_name": u.display_name if u else f"User #{uid}",
                "matched_competences": [{"name": c.name, "level": c.level} for c in matched],
                "score": sum(c.level for c in matched),
            })
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:10]


@router.get("/ai/suggestions", response_model=list[AISuggestionOut])
def list_ai_suggestions(db: Db, user: CurrentUser) -> list[AISuggestion]:
    return list(db.scalars(
        select(AISuggestion)
        .where(AISuggestion.user_id == user.id)
        .order_by(AISuggestion.created_at.desc())
        .limit(20)
    ))


@router.post("/ai/suggestions/{suggestion_id}/resolve", response_model=AISuggestionOut)
def resolve_ai_suggestion(suggestion_id: int, payload: AISuggestionResolve, db: Db, user: CurrentUser) -> AISuggestion:
    item = db.get(AISuggestion, suggestion_id)
    if not item:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if item.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    item.status = payload.status
    item.reason = payload.reason
    item.reviewed_by = user.id
    from datetime import UTC, datetime

    item.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return item


@router.get("/recommendations/scenario/{goal_id}", response_model=AIRecommendation)
def scenario_analysis(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    if is_llm_available():
        answer = llm_complete_sync(
            SYSTEM_PROMPT,
            f"Цель: {goal.title}. Описание: {goal.description}. "
            f"Предложи 3 сценария развития (оптимистичный, реалистичный, пессимистичный) с оценкой рисков.",
        )
        if answer:
            return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)
    return AIRecommendation(suggestion="AI-моделирование сценариев будет подключено после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/risk-analysis/{goal_id}", response_model=AIRecommendation)
def risk_analysis(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    if is_llm_available():
        answer = llm_complete_sync(
            SYSTEM_PROMPT,
            f"Цель: {goal.title}. Ресурсы: {goal.required_resources}. "
            f"Проведи анализ рисков: главные угрозы, вероятность, влияние, стратегии снижения.",
        )
        if answer:
            return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)
    return AIRecommendation(suggestion="AI-анализ рисков будет подключён после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/goal-conflicts/{goal_id}", response_model=AIRecommendation)
def goal_conflicts(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    goal = require_goal(db, user.id, goal_id)
    user_goals = list(db.scalars(select(Goal).where(Goal.owner_id == user.id, Goal.id != goal_id).limit(10)))
    if is_llm_available() and user_goals:
        context = "\n".join(f"- {g.title}: {g.description[:100]}" for g in user_goals)
        answer = llm_complete_sync(
            SYSTEM_PROMPT,
            f"Текущая цель: {goal.title}. Другие цели пользователя:\n{context}\n"
            f"Найди потенциальные конфликты между целями (ресурсы, время, приоритеты).",
        )
        if answer:
            return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)
    return AIRecommendation(suggestion="AI-анализ конфликтов целей будет подключён после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/mentoring", response_model=AIRecommendation)
def mentoring(db: Db, user: CurrentUser) -> AIRecommendation:
    if not user.ai_consent:
        return AIRecommendation(suggestion="AI-анализ требует согласия на обработку данных.", source="consent_required", confidence=0.0)
    comps = list(db.scalars(select(Competence).where(Competence.user_id == user.id, Competence.is_visible == True)))
    if is_llm_available() and comps:
        context = "\n".join(f"- {c.name} (уровень {c.level})" for c in comps)
        answer = llm_complete_sync(
            SYSTEM_PROMPT,
            f"Компетенции пользователя:\n{context}\n"
            f"Предложи направления для обучения и наставничества на основе текущего профиля.",
        )
        if answer:
            return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)
    return AIRecommendation(suggestion="AI-рекомендации по обучению будут подключены после настройки LLM.", source="stub", confidence=0.0)


@router.get("/recommendations/patterns", response_model=AIRecommendation)
def extract_patterns(db: Db, user: CurrentUser) -> AIRecommendation:
    decisions = list(db.scalars(select(Decision).where(Decision.author_id == user.id).limit(20)))
    if is_llm_available() and decisions:
        context = "\n".join(f"- {d.title}: {d.proposal[:100]} ({d.status})" for d in decisions)
        answer = llm_complete_sync(
            SYSTEM_PROMPT,
            f"История решений пользователя:\n{context}\n"
            f"Извлеки закономерности в принятии решений: типичные подходы, предпочтения, слепые зоны.",
        )
        if answer:
            return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)
    return AIRecommendation(suggestion="AI-извлечение закономерностей будет подключено после настройки LLM.", source="stub", confidence=0.0)
