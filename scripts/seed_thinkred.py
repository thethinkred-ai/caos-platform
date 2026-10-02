# -*- coding: utf-8 -*-
"""Create the ThinkRed project in CAOS through the public API.

The critique's demonstration principle: ThinkRed must be the first real
user of its own platform. The bot audit (02.10.2026) confirmed the
production database holds three orphan draft goals and nothing else.

Run by the OWNER (content is authored under your account):

    python scripts/seed_thinkred.py \
        --url https://api-caos.thinkred.ru/api/v1 \
        --email you@example.com --password '...'

Idempotent: everything is searched by title before creation, so the
script can be re-run safely; existing objects are linked, not duplicated.

What it creates (the ThinkRed project structure):
  1. Problem «Воспроизводство организованной практики» (if absent)
  2. Strategic goal «Система массового марксистского образования» with
     measurable criteria and a deadline, linked to the problem
  3. Five sub-goals (courses, analytics, site, simulator, CAOS itself),
     each linked `concretizes` to the strategic goal, with criteria
  4. Project «ThinkRed» linked to the strategic goal (project_goals)
  5. Stage tasks with deadlines inside the project
  6. Prints a report with every ID
"""

import argparse
import sys
from datetime import datetime, timedelta

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the ThinkRed project structure in CAOS")
    parser.add_argument("--url", default="https://api-caos.thinkred.ru/api/v1")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    return parser.parse_args()


class Caos:
    def __init__(self, base_url: str, email: str, password: str) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=30)
        response = self.client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        me = self.client.get("/auth/me")
        me.raise_for_status()
        self.user = me.json()
        print(f"вошли как: {self.user['display_name']} (id {self.user['id']})")

    # -- lookup helpers (idempotency) ------------------------------------
    def find(self, path: str, title: str) -> dict | None:
        items = self.client.get(path).json()
        for item in items:
            if item.get("title") == title or item.get("name") == title:
                return item
        return None

    def goal(self, title: str, **payload) -> dict:
        existing = self.find("/goals", title)
        if existing:
            print(f"  = цель существует: «{title}» (id {existing['id']})")
            return existing
        created = self.client.post("/goals", json={"title": title, **payload})
        created.raise_for_status()
        goal = created.json()
        print(f"  + цель: «{title}» (id {goal['id']})")
        return goal

    def problem(self, title: str, description: str, current_state: str, scope: str) -> dict:
        existing = self.find("/problems", title)
        if existing:
            print(f"  = проблема существует: «{title}» (id {existing['id']})")
            return existing
        created = self.client.post("/problems", json={
            "title": title, "description": description,
            "current_state": current_state, "scope": scope,
        })
        created.raise_for_status()
        problem = created.json()
        print(f"  + проблема: «{title}» (id {problem['id']})")
        return problem

    def relation(self, source_id: int, target_id: int, relation_type: str, rationale: str) -> None:
        existing = self.client.get(f"/goals/{source_id}/relations").json()
        for rel in existing:
            if rel["target_goal_id"] == target_id and rel["relation_type"] == relation_type:
                return
        response = self.client.post(f"/goals/{source_id}/relations", json={
            "target_goal_id": target_id, "relation_type": relation_type, "rationale": rationale,
        })
        if response.status_code == 201:
            print(f"  + связь: {relation_type} {source_id} -> {target_id}")
        else:
            print(f"  ! связь отклонена ({response.status_code}): {response.text[:120]}")

    def criterion(self, goal_id: int, name: str, **payload) -> None:
        existing = self.client.get(f"/goals/{goal_id}/criteria").json()
        if any(c["name"] == name for c in existing):
            return
        created = self.client.post(f"/goals/{goal_id}/criteria", json={"name": name, **payload})
        created.raise_for_status()
        print(f"  + критерий: «{name}» (цель {goal_id})")


def main() -> int:
    args = parse_args()
    caos = Caos(args.url, args.email, args.password)
    year_end = (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%dT23:59:00Z")

    print("\n[1/5] Проблема-основание")
    problem = caos.problem(
        title="Воспроизводство организованной практики",
        description="Организации воспроизводят кружки и медиа, но плохо воспроизводят организованную практику: "
                    "навыки совместной работы держатся на отдельных людях и теряются при их уходе.",
        current_state="Курсы и статьи дают знания, но не дают опыта коллективного целеполагания и проверки результатов.",
        scope="Коллективы левого движения: кружки, профсоюзные инициативы, просветительские проекты.",
    )

    print("\n[2/5] Стратегическая цель с критериями")
    strategic = caos.goal(
        title="Система массового марксистского образования XXI века",
        description="Целостная система: курсы дают теорию, медиа — анализ текущего момента, симулятор — практику решений, "
                    "CAOS — практику коллективного целеполагания. Не набор продуктов, а воспроизводимый цикл подготовки.",
        problem_id=problem["id"],
        expected_outcome="Самовоспроизводящийся цикл: выпускник курса становится участником целей коллектива и готовит следующих.",
        required_resources="Команда ThinkRed, платформа Stepik, сайт, открытый код CAOS.",
        deadline=year_end,
    )
    caos.criterion(strategic["id"], "Опубликованные курсы", criterion_type="quantitative", baseline="0", target_value="4", unit="курса")
    caos.criterion(strategic["id"], "Активные цели в CAOS", criterion_type="quantitative", baseline="0", target_value="10", unit="целей")
    caos.criterion(strategic["id"], "Проверенные результаты", criterion_type="quantitative", baseline="0", target_value="20", unit="результатов")

    print("\n[3/5] Подцели (concretizes)")
    subgoals = [
        (
            "Цикл курсов на Stepik: логика, политэкономия, ленинский этап",
            "Три базовых курса (Наука логики Гегеля, Капитал Маркса, Ленин «Карл Маркс») доведены до конца "
            "и связаны в последовательную траекторию с проверяемым завершением.",
            [("Опубликованные курсы", "3", "курса"), ("Завершаемость траектории", "60", "%")],
        ),
        (
            "Регулярная аналитика текущего момента",
            "Еженедельный марксистский анализ событий на сайте и в каналах — не комментарии, а инструмент классовой ориентировки.",
            [("Публикации в месяц", "4", "разборa")],
        ),
        (
            "Политический симулятор: практика решений",
            "game.thinkred.ru даёт проверить усвоение категорий на симулированных ситуациях классовой борьбы.",
            [("Игроков прошло сценарии", "500", "человек")],
        ),
        (
            "CAOS: платформа коллективного целеполагания",
            "Открытая система (v0.2 выпущена), в которой коллективы ведут цели, обязательства и проверяемые результаты. "
            "Ключевой критерий — мы сами работаем в ней: этот граф и есть приёмочная проверка.",
            [("Коллективов ведёт цели", "3", "коллектива")],
        ),
        (
            "Организационная инфраструктура ThinkRed",
            "Бэкапы, деплой, документация и финансирование проекта — воспроизводимы и не держатся на одном человеке.",
            [("Инструкций задокументировано", "5", "runbook'ов")],
        ),
    ]
    created_subgoals = []
    for title, description, criteria in subgoals:
        sub = caos.goal(title=title, description=description)
        caos.relation(sub["id"], strategic["id"], "concretizes",
                      f"«{title}» — необходимая составляющая стратегической цели.")
        for crit_name, target, unit in criteria:
            caos.criterion(sub["id"], crit_name, criterion_type="quantitative", target_value=target, unit=unit)
        created_subgoals.append(sub)

    print("\n[4/5] Проект ThinkRed и связка с целью")
    project = caos.find("/projects", "ThinkRed")
    if project:
        print(f"  = проект существует (id {project['id']})")
    else:
        created = caos.client.post("/projects", json={
            "title": "ThinkRed",
            "description": "Домашний проект коллектива: образование, аналитика, инструменты. "
                           "Куратор — владелец целей; участники добавляются через участие в целях.",
            "goal_id": strategic["id"],
        })
        created.raise_for_status()
        project = created.json()
        print(f"  + проект «ThinkRed» (id {project['id']})")

    print("\n[5/5] Этапы-задачи с сроками")
    stages = [
        ("Свести три курса в единую траекторию с входным и итоговым тестированием", 30),
        ("Составить редакционный календарь аналитики на квартал", 14),
        ("Провести гейм-сессию симулятора с кружком и собрать обратную связь", 45),
        ("Завести рабочие цели команды в CAOS и провести первую верификацию результата", 21),
        ("Опубликовать runbook: восстановление, бэкапы, деплой", 30),
    ]
    existing_tasks = caos.client.get(f"/projects/{project['id']}/tasks").json()
    existing_titles = {t["title"] for t in existing_tasks}
    for title, days in stages:
        if title in existing_titles:
            print(f"  = задача существует: «{title}»")
            continue
        deadline = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%dT23:59:00Z")
        created = caos.client.post(f"/projects/{project['id']}/tasks", json={
            "title": title, "description": "", "deadline": deadline,
        })
        created.raise_for_status()
        print(f"  + задача: «{title}» (срок {deadline[:10]})")

    print("\nГотово. Дальше вручную:")
    print("  1. Провести стратегическую цель по процедуре: Предложить → Решение → Принять → Активировать.")
    print("     (Сознательно не делается скриптом: коллективное признание — процедура, а не вставка в базу.)")
    print("  2. Позвать участников: каждая подцель → «Присоединиться» с ролью.")
    print("  3. Взять первые обязательства в «Моей деятельности».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
