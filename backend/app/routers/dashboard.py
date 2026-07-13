from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Goal, Problem, Project, ProjectMember, Task, User
from ..schemas import NextActionOut

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/next-action", response_model=NextActionOut)
def next_action(db: Db, user: CurrentUser) -> NextActionOut:
    open_problems = db.scalar(select(Problem).where(Problem.author_id == user.id, Problem.status == "open"))
    if open_problems:
        return NextActionOut(
            label=f"Сформулируйте цель для проблемы «{open_problems.title}»",
            section="goals",
            reason="У вас есть открытая проблема без цели.",
        )

    draft_goals = db.scalar(select(Goal).where(Goal.owner_id == user.id, Goal.status == "draft"))
    if draft_goals:
        return NextActionOut(
            label=f"Создайте проект для цели «{draft_goals.title}»",
            section="projects",
            reason="Цель в статусе черновика — нужен проект.",
        )

    planned_projects = db.scalar(
        select(Project).where(Project.owner_id == user.id, Project.status == "planned")
    )
    if planned_projects:
        return NextActionOut(
            label=f"Добавьте задачи в проект «{planned_projects.title}»",
            section="projects",
            reason="Проект спланирован, но задачи не созданы.",
        )

    member_projects = db.scalars(
        select(Project).join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.user_id == user.id, Project.status != "done"
        )
    )
    todo_task = None
    for project in member_projects:
        todo_task = db.scalar(select(Task).where(Task.project_id == project.id, Task.status == "todo"))
        if todo_task:
            break

    if todo_task:
        return NextActionOut(
            label=f"Выполните задачу «{todo_task.title}»",
            section="projects",
            reason="У вас есть невыполненная задача в проекте.",
        )

    return NextActionOut(
        label="Зафиксируйте новую проблему",
        section="problems",
        reason="Нет активных задач — начните новый цикл деятельности.",
    )
