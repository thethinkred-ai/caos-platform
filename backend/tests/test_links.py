"""Project-goal M2M and knowledge relations tests (Track C7)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Общая цель"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def test_project_serves_multiple_goals(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal_a = _goal(owner, "Первая цель")
    goal_b = _goal(owner, "Вторая цель")
    project = owner.post(
        "/api/v1/projects", json={"title": "Общий проект", "description": "D", "goal_id": goal_a["id"]}
    ).json()

    # The legacy link (goal_id) is visible as one project_goals row...
    listed = owner.get(f"/api/v1/projects/{project['id']}/goals")
    assert [g["goal_id"] for g in listed.json()] == [goal_a["id"]]

    # ...and a second goal can be linked explicitly.
    second = owner.post(
        f"/api/v1/projects/{project['id']}/goals", json={"goal_id": goal_b["id"], "relation_type": "supports"}
    )
    assert second.status_code == 201, second.text
    listed = owner.get(f"/api/v1/projects/{project['id']}/goals")
    assert {g["goal_id"] for g in listed.json()} == {goal_a["id"], goal_b["id"]}

    # Duplicate link rejected.
    assert owner.post(f"/api/v1/projects/{project['id']}/goals", json={"goal_id": goal_b["id"]}).status_code == 409


def test_m2m_link_grants_goal_access_to_project_member(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner, "Цель через M2M")
    other_goal = _goal(owner, "Вторая цель")
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D"}).json()
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": member_user["id"], "role": "member"})

    # Before linking, the member cannot see the goal.
    assert member.get(f"/api/v1/goals/{goal['id']}/relations").status_code == 403

    owner.post(f"/api/v1/projects/{project['id']}/goals", json={"goal_id": goal["id"]})
    assert member.get(f"/api/v1/goals/{goal['id']}/relations").status_code == 200
    # Unlinked goals remain invisible.
    assert member.get(f"/api/v1/goals/{other_goal['id']}/relations").status_code == 403


def test_project_owner_only_links_goals(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D"}).json()
    # Stranger neither owns the project nor sees the goal.
    assert stranger.post(
        f"/api/v1/projects/{project['id']}/goals", json={"goal_id": goal["id"]}
    ).status_code in (403, 404)


def test_knowledge_relations_to_goal_and_result(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner, "Цель со знанием")
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D", "goal_id": goal["id"]}).json()
    knowledge = owner.post(
        "/api/v1/knowledge",
        json={"title": "Анализ курса", "content": "Завершаемость выросла", "project_id": project["id"]},
    ).json()
    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Результат"}).json()

    linked_goal = owner.post(
        f"/api/v1/knowledge/{knowledge['id']}/relations",
        json={"target_type": "goal", "target_id": goal["id"], "relation_type": "supports"},
    )
    assert linked_goal.status_code == 201, linked_goal.text

    linked_result = owner.post(
        f"/api/v1/knowledge/{knowledge['id']}/relations",
        json={"target_type": "result", "target_id": result["id"], "relation_type": "evidences"},
    )
    assert linked_result.status_code == 201

    relations = owner.get(f"/api/v1/knowledge/{knowledge['id']}/relations")
    assert {r["relation_type"] for r in relations.json()} == {"supports", "evidences"}

    # Invalid relation type and duplicates rejected.
    assert owner.post(
        f"/api/v1/knowledge/{knowledge['id']}/relations",
        json={"target_type": "goal", "target_id": goal["id"], "relation_type": "loves"},
    ).status_code == 422
    assert owner.post(
        f"/api/v1/knowledge/{knowledge['id']}/relations",
        json={"target_type": "goal", "target_id": goal["id"], "relation_type": "supports"},
    ).status_code == 409


def test_knowledge_relation_requires_target_access(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    knowledge = stranger.post("/api/v1/knowledge", json={"title": "Заметка", "content": "Текст"}).json()

    response = stranger.post(
        f"/api/v1/knowledge/{knowledge['id']}/relations",
        json={"target_type": "goal", "target_id": goal["id"]},
    )
    assert response.status_code == 403
