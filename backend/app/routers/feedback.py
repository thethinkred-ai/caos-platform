"""Обратная связь и детектор «пользователь застрял».

Задача модуля — не ждать, пока человек сам найдёт форму обратной связи,
а заметить, что он остановился, и предложить написать, что именно не так.

«Застрял» здесь определяется по проверяемым признакам в базе, а не по
догадкам: сколько объектов человек создал и на каком шаге остановился.
Признаки честно перечислены в ответе (checklist), чтобы пользователь
не отвечал на пустой вопрос «что не так?».
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import (
    Decision,
    Feedback,
    Goal,
    KnowledgeItem,
    Problem,
    Project,
    ProjectMember,
    Task,
    User,
)
from ..schemas import FeedbackCreate, FeedbackOut, StuckState

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]

# Тексты подсказок. Формулировка зависит от этапа: человеку, который ещё
# ничего не создал, нельзя задавать вопрос «что улучшить в проекте».
STAGE_TEXT: dict[str, tuple[str, list[str]]] = {
    "empty_after_hour": (
        "Вы зашли на платформу, но пока ничего не создали. Это нормально — "
        "первый шаг здесь неочевиден. Напишите, что вы хотели сделать и где "
        "остановились: мы исправим интерфейс, а не только подскажем вам лично.",
        [
            "Не понял, с чего начать",
            "Не нашёл, где создать цель",
            "Не понял, чем цель отличается от проекта",
            "Что-то не открылось или выдало ошибку",
            "Другое",
        ],
    ),
    "empty_after_day": (
        "Вы зарегистрировались больше суток назад и пока ничего не создали. "
        "Если платформа не подошла или что-то не сработало — напишите пару "
        "строк. Нам важно понять, где именно вы застряли.",
        [
            "Не понял, с чего начать",
            "Не нашёл нужный раздел",
            "Ожидал другого — опишу",
            "Что-то не открылось или выдало ошибку",
            "Другое",
        ],
    ),
    "goal_without_project": (
        "У вас есть цель, но нет проекта и вы не в команде. Обычно на этом "
        "шаге непонятно, как перейти от цели к исполнителям. Что здесь "
        "неочевидно?",
        [
            "Не понял, как создать проект из цели",
            "Не понял, как пригласить людей",
            "Не нашёл, где задачи",
            "Всё понятно, просто ещё не сделал",
        ],
    ),
    "project_without_tasks": (
        "Проект создан, но задач в нём нет. Если вы ждали, что задачи "
        "появятся сами или не нашли кнопку — скажите, поправим.",
        [
            "Не нашёл, где добавить задачу",
            "Ждал, что задачи создадутся из цели",
            "Не понял, кому назначать исполнителя",
            "Другое",
        ],
    ),
    "tasks_without_assignee": (
        "Задачи в проекте есть, но ни одна не назначена на исполнителя — "
        "так проект не сдвинется. Если это неочевидно, напишите.",
        [
            "Не понял, как назначить исполнителя",
            "Не хочу назначать на себя",
            "Не нашёл участников",
            "Другое",
        ],
    ),
}


def _count(db: Session, model, field: str, user_id: int) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(getattr(model, field) == user_id)) or 0)


def detect_stuck(db: Session, user: User) -> StuckState:
    goals = _count(db, Goal, "owner_id", user.id)
    projects = _count(db, Project, "owner_id", user.id)
    problems = _count(db, Problem, "author_id", user.id)
    knowledge = _count(db, KnowledgeItem, "author_id", user.id)
    decisions = _count(db, Decision, "author_id", user.id)
    memberships = _count(db, ProjectMember, "user_id", user.id)
    assigned_tasks = _count(db, Task, "assignee_id", user.id)

    own_project_ids = list(db.scalars(select(Project.id).where(Project.owner_id == user.id)))
    own_tasks = 0
    unassigned = 0
    if own_project_ids:
        own_tasks = int(db.scalar(
            select(func.count()).select_from(Task).where(Task.project_id.in_(own_project_ids))
        ) or 0)
        unassigned = int(db.scalar(
            select(func.count()).select_from(Task).where(
                Task.project_id.in_(own_project_ids), Task.assignee_id.is_(None)
            )
        ) or 0)

    created_at = user.created_at or datetime.utcnow()
    hours = max((datetime.utcnow() - created_at).total_seconds() / 3600.0, 0.0)
    objects = {
        "goals": goals,
        "projects": projects,
        "problems": problems,
        "knowledge": knowledge,
        "decisions": decisions,
        "memberships": memberships,
        "tasks_assigned": assigned_tasks,
        "tasks_in_own_projects": own_tasks,
    }

    total_own = goals + projects + problems + knowledge + decisions + memberships

    stage = "moving"
    if total_own == 0 and hours >= 24:
        stage = "empty_after_day"
    elif total_own == 0 and hours >= 1:
        stage = "empty_after_hour"
    elif goals > 0 and projects == 0 and memberships == 0:
        stage = "goal_without_project"
    elif projects > 0 and own_tasks == 0:
        stage = "project_without_tasks"
    elif own_tasks > 0 and unassigned == own_tasks:
        stage = "tasks_without_assignee"

    text, checklist = STAGE_TEXT.get(stage, ("", []))
    return StuckState(
        stuck=stage != "moving",
        stage=stage,
        hours_registered=round(hours, 2),
        message=text,
        checklist=checklist,
        objects=objects,
    )


@router.get("/feedback/stuck", response_model=StuckState)
def stuck_state(db: Db, user: CurrentUser) -> StuckState:
    return detect_stuck(db, user)


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(payload: FeedbackCreate, db: Db, user: CurrentUser) -> Feedback:
    state = detect_stuck(db, user)
    item = Feedback(
        user_id=user.id,
        message=payload.message.strip(),
        page=payload.page,
        kind=payload.kind,
        contact=payload.contact.strip() or user.email,
        stage=state.stage if state.stuck else "",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(db: Db, user: CurrentUser, limit: int = 100) -> list[Feedback]:
    """Список читает рабочая команда. Роли admin в базе пока нет ни у кого,
    поэтому доступ закрыт и остаётся закрытым по умолчанию."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступ только для команды")
    return list(db.scalars(select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)))
