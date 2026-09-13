"""Competence evidence tests (Step 30): competence from practice."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _goal(client, title="Цель с опытом"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def test_fulfilled_commitment_becomes_evidence(client, outbox):
    owner, _ = _user(outbox, "ev@example.com")
    goal = owner.post("/api/v1/goals", json={"title": "Цель с опытом", "description": "D"}).json()
    commitment = owner.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Провёл три занятия по логике"},
    ).json()
    competence = owner.post("/api/v1/competences", json={"name": "Преподавание", "level": 3}).json()

    # An open commitment cannot be evidence yet.
    denied = owner.post(
        f"/api/v1/competences/{competence['id']}/evidence",
        json={"source_type": "commitment_fulfilled", "source_id": commitment["id"], "note": "практика"},
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "INVALID_STATE_TRANSITION"

    owner.post(f"/api/v1/commitments/{commitment['id']}/status", json={"status": "in_progress"})
    owner.post(f"/api/v1/commitments/{commitment['id']}/status", json={"status": "fulfilled"})

    recorded = owner.post(
        f"/api/v1/competences/{competence['id']}/evidence",
        json={"source_type": "commitment_fulfilled", "source_id": commitment["id"], "note": "три занятия проведены"},
    )
    assert recorded.status_code == 201, recorded.text

    listing = owner.get("/api/v1/competences")
    assert listing.json()[0]["evidence_count"] == 1

    evidence = owner.get(f"/api/v1/competences/{competence['id']}/evidence")
    assert evidence.json()[0]["note"] == "три занятия проведены"


def test_verified_result_becomes_evidence_after_verification(client, outbox):
    owner, _ = _user(outbox, "evr@example.com")
    verifier, _ = _user(outbox, "evrverifier@example.com")
    goal = _goal(owner)
    owner.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": verifier.get("/api/v1/auth/me").json()["id"], "role": "expert"},
    )
    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Курс запущен"}).json()
    competence = owner.post("/api/v1/competences", json={"name": "Методология", "level": 2}).json()

    # An unverified result cannot be evidence.
    assert owner.post(
        f"/api/v1/competences/{competence['id']}/evidence",
        json={"source_type": "result_verified", "source_id": result["id"]},
    ).status_code == 409

    verifier.post(
        f"/api/v1/results/{result['id']}/verify",
        json={"status": "verified", "rationale": "Подтверждено"},
    )
    recorded = owner.post(
        f"/api/v1/competences/{competence['id']}/evidence",
        json={"source_type": "result_verified", "source_id": result["id"], "note": "проверено другим участником"},
    )
    assert recorded.status_code == 201


def test_evidence_is_owner_scoped(client, outbox):
    owner, _ = _user(outbox, "evowner@example.com")
    stranger, _ = _user(outbox, "evstranger@example.com")
    competence = owner.post("/api/v1/competences", json={"name": "Логика", "level": 3}).json()

    assert stranger.get(f"/api/v1/competences/{competence['id']}/evidence").status_code == 403
    # Someone else cannot record evidence against a competence they do not own.
    assert stranger.post(
        f"/api/v1/competences/{competence['id']}/evidence",
        json={"source_type": "commitment_fulfilled", "source_id": 1},
    ).status_code == 403
