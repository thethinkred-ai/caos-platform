"""Regression tests for the entity CRUD API (current semantics)."""

from tests.conftest import register_and_login


def _authed_user(client, outbox, email, name):
    """Return (authenticated client for this user, user payload)."""
    from fastapi.testclient import TestClient

    from app.main import app

    own = TestClient(app)
    user = register_and_login(own, outbox, email=email, display_name=name)
    return own, user


def test_problem_goal_decision_vote_flow(client, outbox):
    owner, user = _authed_user(client, outbox, "owner@example.com", "Owner")

    problem = owner.post(
        "/api/v1/problems",
        json={"title": "Нет учебной группы", "description": "Нужна регулярная группа для изучения логики."},
    )
    assert problem.status_code == 201
    assert problem.json()["status"] == "open"

    goal = owner.post(
        "/api/v1/goals",
        json={
            "title": "Запустить учебную группу",
            "description": "Еженедельные занятия с проверяемым результатом.",
            "problem_id": problem.json()["id"],
        },
    )
    assert goal.status_code == 201

    sub_goal = owner.post(
        "/api/v1/goals",
        json={"title": "Составить программу", "description": "Программа на 8 занятий.", "parent_goal_id": goal.json()["id"]},
    )
    assert sub_goal.status_code == 201
    sub_goals = owner.get(f"/api/v1/goals/{goal.json()['id']}/sub-goals")
    assert sub_goals.status_code == 200
    assert [g["id"] for g in sub_goals.json()] == [sub_goal.json()["id"]]

    decision = owner.post(
        "/api/v1/decisions",
        json={
            "title": "Формат занятий",
            "proposal": "Публичные еженедельные сессии.",
            "goal_id": goal.json()["id"],
            "decision_method": "majority",
            "quorum": 1,
        },
    )
    assert decision.status_code == 201
    decision_id = decision.json()["id"]

    vote = owner.post(f"/api/v1/decisions/{decision_id}/vote", json={"variant": "accept", "comment": ""})
    assert vote.status_code == 201
    finalized = owner.post(f"/api/v1/decisions/{decision_id}/finalize")
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "accepted"

    # A finalized decision no longer accepts votes.
    assert owner.post(f"/api/v1/decisions/{decision_id}/vote", json={"variant": "reject"}).status_code == 400


def test_decision_author_controls_events_and_finalization(client, outbox):
    owner, _ = _authed_user(client, outbox, "author@example.com", "Author")
    stranger, _ = _authed_user(client, outbox, "stranger@example.com", "Stranger")

    decision = owner.post(
        "/api/v1/decisions",
        json={"title": "Dec One", "proposal": "The proposal"},
    )
    decision_id = decision.json()["id"]

    assert stranger.post(
        f"/api/v1/decisions/{decision_id}/events",
        json={"event_type": "accepted", "content": "hijack"},
    ).status_code == 403
    assert stranger.post(f"/api/v1/decisions/{decision_id}/finalize").status_code == 403
    assert owner.post(
        f"/api/v1/decisions/{decision_id}/events",
        json={"event_type": "accepted", "content": "ok"},
    ).status_code == 201


def test_project_member_task_flow(client, outbox):
    owner, owner_user = _authed_user(client, outbox, "lead@example.com", "Lead")
    member, member_user = _authed_user(client, outbox, "mate@example.com", "Mate")

    goal = owner.post("/api/v1/goals", json={"title": "Goal One", "description": "Some description"}).json()
    project = owner.post(
        "/api/v1/projects",
        json={"title": "Proj One", "description": "Some description", "goal_id": goal["id"]},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    # Non-member cannot create tasks.
    assert member.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task One", "description": ""},
    ).status_code == 403

    added = owner.post(f"/api/v1/projects/{project_id}/members", json={"user_id": member_user["id"], "role": "member"})
    assert added.status_code == 201

    task = member.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "Task One", "description": ""})
    assert task.status_code == 201
    task_id = task.json()["id"]

    assigned = owner.patch(f"/api/v1/tasks/{task_id}/assign", json={"assignee_id": member_user["id"]})
    assert assigned.status_code == 200
    completed = member.patch(f"/api/v1/tasks/{task_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"

    tasks = owner.get(f"/api/v1/projects/{project_id}/tasks")
    assert tasks.json()[0]["assignee_name"] == "Mate"


def test_problems_are_scoped_to_author(client, outbox):
    first, _ = _authed_user(client, outbox, "a@example.com", "Alice")
    second, _ = _authed_user(client, outbox, "b@example.com", "Bob")

    first.post("/api/v1/problems", json={"title": "Чужая проблема", "description": "d"})
    assert second.get("/api/v1/problems").json() == []
    assert len(first.get("/api/v1/problems").json()) == 1


def test_search_finds_own_content_only(client, outbox):
    owner, _ = _authed_user(client, outbox, "s1@example.com", "Searcher One")
    other, _ = _authed_user(client, outbox, "s2@example.com", "Searcher Two")

    owner.post("/api/v1/problems", json={"title": "Уникальная проблема альфа", "description": "d"})
    other.post("/api/v1/problems", json={"title": "Уникальная проблема бета", "description": "d"})

    results = other.get("/api/v1/search", params={"q": "альфа"})
    assert results.status_code == 200
    assert results.json()["problems"] == []
    results = other.get("/api/v1/search", params={"q": "бета"})
    assert len(results.json()["problems"]) == 1


def test_knowledge_and_competences_smoke(client, outbox):
    owner, _ = _authed_user(client, outbox, "k@example.com", "Kyle")

    goal = owner.post("/api/v1/goals", json={"title": "Goal One", "description": "Some description"}).json()
    project = owner.post("/api/v1/projects", json={"title": "Proj One", "description": "Some description", "goal_id": goal["id"]}).json()

    knowledge = owner.post(
        "/api/v1/knowledge",
        json={"title": "Заметка", "content": "Содержимое", "project_id": project["id"]},
    )
    assert knowledge.status_code == 201

    competence = owner.post("/api/v1/competences", json={"name": "Логика", "level": 3})
    assert competence.status_code == 201
    listing = owner.get("/api/v1/competences")
    assert [c["name"] for c in listing.json()] == ["Логика"]


def test_dashboard_and_audit(client, outbox):
    owner, _ = _authed_user(client, outbox, "dash@example.com", "Dash")
    owner.post("/api/v1/problems", json={"title": "Prob One", "description": "Some description"})

    dashboard = owner.get("/api/v1/next-action")
    assert dashboard.status_code == 200

    audit = owner.get("/api/v1/audit")
    assert audit.status_code == 200
    actions = {event["action"] for event in audit.json()}
    assert "created" in actions
