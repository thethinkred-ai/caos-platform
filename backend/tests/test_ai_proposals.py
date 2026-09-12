"""AI proposal recording tests (Track G1, ADR-0003)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email="ai@example.com"):
    client = TestClient(app)
    register_and_login(client, outbox, email=email, display_name="Ai User")
    return client


def test_ai_output_recorded_as_reviewable_proposal(client, outbox):
    owner = _user(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель для AI", "description": "D"}).json()

    response = owner.get(f"/api/v1/recommendations/decompose/{goal['id']}")
    assert response.status_code == 200

    proposals = owner.get("/api/v1/ai/suggestions").json()
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["endpoint"] == "decompose_goal"
    assert proposal["target_type"] == "goal"
    assert proposal["target_id"] == goal["id"]
    assert proposal["confidence"] is not None
    assert proposal["model_name"]  # source is always recorded (stub or llm:model)
    assert proposal["reviewed_by"] is None


def test_resolve_records_reviewer(client, outbox):
    owner = _user(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель для ревью", "description": "D"}).json()
    owner.get(f"/api/v1/recommendations/decompose/{goal['id']}")
    proposal = owner.get("/api/v1/ai/suggestions").json()[0]

    resolved = owner.post(
        f"/api/v1/ai/suggestions/{proposal['id']}/resolve",
        json={"status": "accepted", "reason": "Декомпозиция разумная"},
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["status"] == "accepted"
    assert body["reviewed_by"] == owner.get("/api/v1/auth/me").json()["id"]
    assert body["reviewed_at"] is not None
