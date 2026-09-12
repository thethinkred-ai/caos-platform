"""Goal lifecycle tests (Track C2): state machine, ownership, audit."""

from tests.conftest import register_and_login


def _transition(client, goal_id, action):
    return client.post(f"/api/v1/goals/{goal_id}/transition", json={"action": action})


def _goal(client, title="Живая цель"):
    response = client.post("/api/v1/goals", json={"title": title, "description": "Описание"})
    assert response.status_code == 201, response.text
    return response.json()


def _owner(outbox, email="cycle@example.com"):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name="Cycle Owner")
    return client, user


def test_full_lifecycle_happy_path(client, outbox):
    owner, _ = _owner(outbox)
    goal = _goal(owner)
    assert goal["status"] == "draft"

    for action, expected in [
        ("propose", "proposed"),
        ("accept", "accepted"),
        ("activate", "active"),
        ("suspend", "suspended"),
        ("resume", "active"),
        ("report-achieved", "achieved"),
        ("verify", "verified"),
        ("close", "closed"),
    ]:
        response = _transition(owner, goal["id"], action)
        assert response.status_code == 200, (action, response.text)
        assert response.json()["status"] == expected


def test_side_exits(client, outbox):
    owner, _ = _owner(outbox)
    goal = _goal(owner, "Отвергнутая цель")
    _transition(owner, goal["id"], "propose")
    assert _transition(owner, goal["id"], "reject").json()["status"] == "rejected"
    assert _transition(owner, goal["id"], "close").json()["status"] == "closed"


def test_invalid_transition_rejected(client, outbox):
    owner, _ = _owner(outbox)
    goal = _goal(owner)

    # Draft cannot jump straight to active (INV-1: no recognition bypass).
    response = _transition(owner, goal["id"], "activate")
    assert response.status_code == 409
    # Closed goals are final.
    _transition(owner, goal["id"], "propose")
    _transition(owner, goal["id"], "reject")
    _transition(owner, goal["id"], "close")
    assert _transition(owner, goal["id"], "propose").status_code == 409


def test_unknown_action_rejected(client, outbox):
    owner, _ = _owner(outbox)
    goal = _goal(owner)
    response = _transition(owner, goal["id"], "harness-magic")
    assert response.status_code == 422


def test_only_owner_can_transition(client, outbox):
    from fastapi.testclient import TestClient

    from app.main import app

    owner, _ = _owner(outbox)
    stranger = TestClient(app)
    register_and_login(stranger, outbox, email="stranger@example.com", display_name="Stranger")
    goal = _goal(owner)

    assert _transition(stranger, goal["id"], "propose").status_code == 403


def test_transitions_recorded_in_audit(client, outbox):
    owner, _ = _owner(outbox)
    goal = _goal(owner)
    _transition(owner, goal["id"], "propose")

    audit = owner.get("/api/v1/audit").json()
    actions = {event["action"] for event in audit}
    assert "goal:propose" in actions
