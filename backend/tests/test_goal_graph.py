"""Goal graph tests (Track C1): typed relations, cycles, access, impact."""

from tests.conftest import register_and_login


def _goal(client, title="Цель", **extra):
    return client.post(
        "/api/v1/goals", json={"title": title, "description": "Описание цели", **extra}
    ).json()


def _relate(client, source_id, target_id, relation_type="depends_on", rationale="Обоснование связи"):
    return client.post(
        f"/api/v1/goals/{source_id}/relations",
        json={"target_goal_id": target_id, "relation_type": relation_type, "rationale": rationale},
    )


def _owner(outbox, email="graph@example.com"):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name="Graph Owner")
    return client, user


def test_create_and_list_relation(client, outbox):
    owner, _ = _owner(outbox)
    a, b = _goal(owner, "Цель А"), _goal(owner, "Цель Б")

    created = _relate(owner, a["id"], b["id"], "depends_on", "А зависит от Б")
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["relation_type"] == "depends_on"
    assert body["rationale"].startswith("А зависит")

    listed = owner.get(f"/api/v1/goals/{a['id']}/relations")
    assert listed.status_code == 200
    assert [r["id"] for r in listed.json()] == [body["id"]]


def test_relation_requires_access_to_both_goals(client, outbox):
    from fastapi.testclient import TestClient

    from app.main import app

    owner, _ = _owner(outbox)
    stranger = TestClient(app)
    register_and_login(stranger, outbox, email="stranger@example.com", display_name="Stranger")

    own_goal = _goal(owner, "Своя цель")
    foreign_goal = _goal(stranger, "Чужая цель")

    assert _relate(owner, own_goal["id"], foreign_goal["id"]).status_code == 403
    assert _relate(stranger, foreign_goal["id"], own_goal["id"]).status_code == 403


def test_self_relation_rejected(client, outbox):
    owner, _ = _owner(outbox)
    a = _goal(owner)
    assert _relate(owner, a["id"], a["id"]).status_code == 400


def test_invalid_relation_type_rejected(client, outbox):
    owner, _ = _owner(outbox)
    a, b = _goal(owner, "Альфа"), _goal(owner, "Бета")
    assert _relate(owner, a["id"], b["id"], "loves").status_code == 422


def test_duplicate_relation_rejected(client, outbox):
    owner, _ = _owner(outbox)
    a, b = _goal(owner, "Альфа"), _goal(owner, "Бета")
    assert _relate(owner, a["id"], b["id"], "supports").status_code == 201
    assert _relate(owner, a["id"], b["id"], "supports").status_code == 409
    # A different type on the same pair is a distinct edge.
    assert _relate(owner, a["id"], b["id"], "conflicts_with").status_code == 201


def test_cycle_over_depends_on_rejected(client, outbox):
    owner, _ = _owner(outbox)
    a, b, c = _goal(owner, "Альфа"), _goal(owner, "Бета"), _goal(owner, "Гамма")
    assert _relate(owner, a["id"], b["id"], "depends_on").status_code == 201
    assert _relate(owner, b["id"], c["id"], "depends_on").status_code == 201
    # C -> A would close the loop A -> B -> C -> A.
    assert _relate(owner, c["id"], a["id"], "depends_on").status_code == 400
    # Non-ordering types may loop.
    assert _relate(owner, c["id"], a["id"], "supports").status_code == 201


def test_impact_counts(client, outbox):
    owner, _ = _owner(outbox)
    top = _goal(owner, "Верхняя цель")
    mid = _goal(owner, "Средняя цель")
    leaf = _goal(owner, "Нижняя цель")

    _relate(owner, mid["id"], top["id"], "depends_on")   # mid depends on top
    _relate(owner, leaf["id"], mid["id"], "depends_on")  # leaf depends on mid
    _relate(owner, leaf["id"], top["id"], "supports")

    owner.post("/api/v1/projects", json={"title": "Проект", "description": "D", "goal_id": top["id"]})
    owner.post("/api/v1/decisions", json={"title": "Решение", "proposal": "P", "goal_id": top["id"]})

    impact = owner.get(f"/api/v1/goals/{top['id']}/impact")
    assert impact.status_code == 200
    body = impact.json()
    # leaf reaches top transitively through mid.
    assert body["direct_dependents"] == 1
    assert body["transitive_dependents"] == 1
    assert body["supporters"] == 1
    assert body["projects"] == 1
    assert body["decisions"] == 1


def test_impact_requires_access(client, outbox):
    from fastapi.testclient import TestClient

    from app.main import app

    owner, _ = _owner(outbox)
    stranger = TestClient(app)
    register_and_login(stranger, outbox, email="stranger@example.com", display_name="Stranger")
    goal = _goal(owner, "Секретная цель")
    assert stranger.get(f"/api/v1/goals/{goal['id']}/impact").status_code == 403


def test_explain_chain_assembles_full_trace(client, outbox):
    from fastapi.testclient import TestClient

    from app.main import app

    owner, _ = _owner(outbox, "explain@example.com")
    stranger = TestClient(app)
    register_and_login(stranger, outbox, email="stranger@example.com", display_name="Stranger")

    problem = owner.post("/api/v1/problems", json={"title": "Нет учебной группы", "description": "d"}).json()
    goal = owner.post(
        "/api/v1/goals",
        json={"title": "Запустить группу", "description": "D", "problem_id": problem["id"]},
    ).json()
    decision = owner.post(
        "/api/v1/decisions",
        json={"title": "Формат", "proposal": "Еженедельные встречи", "goal_id": goal["id"]},
    ).json()
    commitment = owner.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Готовлю программу"},
    ).json()
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D", "goal_id": goal["id"]}).json()
    task = owner.post(
        f"/api/v1/projects/{project['id']}/tasks", json={"title": "Составить план", "description": ""}
    ).json()
    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Группа работает"}).json()

    explain = owner.get(f"/api/v1/goals/{goal['id']}/explain")
    assert explain.status_code == 200, explain.text
    body = explain.json()
    kinds = [(n["kind"], n["id"]) for n in body["chain"]]
    assert ("problem", problem["id"]) in kinds
    assert ("decision", decision["id"]) in kinds
    assert ("commitment", commitment["id"]) in kinds
    assert ("task", task["id"]) in kinds
    assert ("result", result["id"]) in kinds
    assert body["counts"] == {"decisions": 1, "commitments": 1, "tasks": 1, "results": 1}

    # The trace is access-scoped with the goal itself.
    assert stranger.get(f"/api/v1/goals/{goal['id']}/explain").status_code == 403
