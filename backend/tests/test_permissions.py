"""Permission matrix tests (Track D1): capabilities by contextual role,
collective recognition instead of owner-only power."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Общая цель"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def _participate(owner, goal_id, user, role="contributor"):
    response = owner.post(
        f"/api/v1/goals/{goal_id}/participations",
        json={"user_id": user["id"], "role": role},
    )
    assert response.status_code == 201, response.text


def _transition(client, goal_id, action):
    return client.post(f"/api/v1/goals/{goal_id}/transition", json={"action": action})


def _recognize_via_decision(owner, participant, goal_id):
    """Collective recognition: decision on the goal, majority vote, finalize."""
    decision = owner.post(
        "/api/v1/decisions",
        json={"title": "Признать цель", "proposal": "Признать цель коллективно", "goal_id": goal_id},
    ).json()
    owner.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})
    participant.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})
    finalized = owner.post(f"/api/v1/decisions/{decision['id']}/finalize")
    assert finalized.json()["status"] == "accepted"


def test_coordinator_can_transition_but_contributor_cannot(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    coordinator, coordinator_user = _user(outbox, "coord@example.com")
    contributor, contributor_user = _user(outbox, "contrib@example.com")
    goal = _goal(owner)
    _participate(owner, goal["id"], coordinator_user, "coordinator")
    _participate(owner, goal["id"], contributor_user, "contributor")

    assert _transition(owner, goal["id"], "propose").status_code == 200
    assert _transition(coordinator, goal["id"], "review").status_code == 200
    response = _transition(contributor, goal["id"], "accept")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_SCOPE"


def test_collective_recognition_required_when_participants_exist(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner)
    _participate(owner, goal["id"], member_user, "contributor")
    _transition(owner, goal["id"], "propose")

    # The owner alone can no longer recognize a shared goal.
    response = _transition(owner, goal["id"], "accept")
    assert response.status_code == 409
    assert response.json()["code"] == "RECOGNITION_REQUIRED"

    # Collective decision unlocks recognition.
    _recognize_via_decision(owner, member, goal["id"])
    accepted = _transition(owner, goal["id"], "accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"


def test_solo_goal_accepted_without_collective_decision(client, outbox):
    owner, _ = _user(outbox, "solo@example.com")
    goal = _goal(owner, "Личная цель")
    _transition(owner, goal["id"], "propose")
    assert _transition(owner, goal["id"], "accept").status_code == 200


def test_verification_requires_expert_role(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    expert, expert_user = _user(outbox, "expert@example.com")
    contributor, contributor_user = _user(outbox, "contrib@example.com")
    goal = _goal(owner)
    _participate(owner, goal["id"], expert_user, "expert")
    _participate(owner, goal["id"], contributor_user, "contributor")

    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Результат"}).json()

    denied = contributor.post(
        f"/api/v1/results/{result['id']}/verify",
        json={"status": "verified", "rationale": "Не моя роль, но хочу"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "FORBIDDEN_SCOPE"

    allowed = expert.post(
        f"/api/v1/results/{result['id']}/verify",
        json={"status": "verified", "rationale": "Проверено как эксперт"},
    )
    assert allowed.status_code == 200


def test_coordinator_manages_roles(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    coordinator, coordinator_user = _user(outbox, "coord@example.com")
    newcomer, newcomer_user = _user(outbox, "new@example.com")
    goal = _goal(owner)
    _participate(owner, goal["id"], coordinator_user, "coordinator")

    invited = coordinator.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": newcomer_user["id"], "role": "observer"},
    )
    assert invited.status_code == 201

    promoted = coordinator.patch(
        f"/api/v1/goals/{goal['id']}/participations/{newcomer_user['id']}",
        json={"role": "contributor"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "contributor"


def test_observer_cannot_create_relations(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    observer, observer_user = _user(outbox, "observer@example.com")
    goal_a = _goal(owner, "Цель одна")
    goal_b = _goal(owner, "Цель две")
    _participate(owner, goal_a["id"], observer_user, "observer")
    # The observer needs access to goal_b too — via participation.
    _participate(owner, goal_b["id"], observer_user, "observer")

    response = observer.post(
        f"/api/v1/goals/{goal_a['id']}/relations",
        json={"target_goal_id": goal_b["id"], "relation_type": "supports", "rationale": "Хочу связать"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_SCOPE"
