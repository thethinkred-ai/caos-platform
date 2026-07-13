from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..llm import is_llm_available, llm_complete_sync
from ..models import Goal, KnowledgeItem, Problem, Project, User
from ..schemas import AIRecommendation

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
settings = get_settings()

SYSTEM_PROMPT = (
    "You are an AI assistant for a collaborative action platform (CAOS). "
    "Users formulate problems, set goals, run projects, and build a knowledge base. "
    "Respond concisely in Russian. Be specific and actionable."
)


def _stub_similar_problems(db: Session, problem_id: int) -> AIRecommendation:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    others = list(db.scalars(
        select(Problem).where(Problem.id != problem_id).limit(5)
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


def _stub_find_knowledge(db: Session, query: str) -> AIRecommendation:
    items = list(db.scalars(select(KnowledgeItem).limit(5)))
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


def _stub_decompose_goal(db: Session, goal_id: int) -> AIRecommendation:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return AIRecommendation(
        suggestion=f"Предлагается разбить цель «{goal.title}» на: 1) исследование, 2) планирование, 3) реализация, 4) оценка.",
        source="heuristic",
        confidence=0.2,
    )


def _llm_similar_problems(db: Session, problem_id: int) -> AIRecommendation:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    others = list(db.scalars(select(Problem).where(Problem.id != problem_id).limit(10)))
    context = f"Проблема: {problem.title}\nОписание: {problem.description}\n\nДругие проблемы:\n"
    context += "\n".join(f"- {p.title}: {p.description[:80]}" for p in others) or "Нет других проблем."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Найди 3 наиболее релевантные проблемы из списка ниже и объясни почему.\n{context}",
    )
    if not answer:
        return _stub_similar_problems(db, problem_id)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


def _llm_similar_people(db: Session, user: User) -> AIRecommendation:
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Пользователь: {user.display_name}. Подскажи, как найти единомышленников для совместной деятельности над проблемами и целями.",
    )
    if not answer:
        return _stub_similar_people(db, user)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.6)


def _llm_find_knowledge(db: Session, query: str) -> AIRecommendation:
    items = list(db.scalars(select(KnowledgeItem).limit(10)))
    context = "\n".join(f"- {k.title}: {k.content[:100]}" for k in items) or "База знаний пуста."
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Найди релевантные знания по запросу «{query}».\nДоступные элементы:\n{context}",
    )
    if not answer:
        return _stub_find_knowledge(db, query)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


def _llm_decompose_goal(db: Session, goal_id: int) -> AIRecommendation:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    projects = list(db.scalars(select(Project).where(Project.goal_id == goal_id).limit(5)))
    context = f"Цель: {goal.title}\nОписание: {goal.description}\n"
    if projects:
        context += "Существующие проекты:\n" + "\n".join(f"- {p.title} ({p.status})" for p in projects)
    answer = llm_complete_sync(
        SYSTEM_PROMPT,
        f"Предложи декомпозицию цели на 3-5 подзадач с кратким обоснованием.\n{context}",
    )
    if not answer:
        return _stub_decompose_goal(db, goal_id)
    return AIRecommendation(suggestion=answer, source=f"llm:{settings.ai_model}", confidence=0.7)


@router.get("/recommendations/similar-problems/{problem_id}", response_model=AIRecommendation)
def similar_problems(problem_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_similar_problems(db, problem_id)
    return _stub_similar_problems(db, problem_id)


@router.get("/recommendations/people", response_model=AIRecommendation)
def similar_people(db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_similar_people(db, user)
    return _stub_similar_people(db, user)


@router.get("/recommendations/knowledge", response_model=AIRecommendation)
def find_knowledge(db: Db, user: CurrentUser, q: str = Query(min_length=2, max_length=200)) -> AIRecommendation:
    if is_llm_available():
        return _llm_find_knowledge(db, q)
    return _stub_find_knowledge(db, q)


@router.get("/recommendations/decompose/{goal_id}", response_model=AIRecommendation)
def decompose_goal(goal_id: int, db: Db, user: CurrentUser) -> AIRecommendation:
    if is_llm_available():
        return _llm_decompose_goal(db, goal_id)
    return _stub_decompose_goal(db, goal_id)


@router.get("/ai/status")
def ai_status(user: CurrentUser) -> dict:
    return {
        "llm_available": is_llm_available(),
        "model": settings.ai_model if is_llm_available() else None,
        "base_url": settings.ai_base_url if is_llm_available() else None,
    }
