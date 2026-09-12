"""Results, evidence, verification tests (Track C5, INV-3/INV-4)."""

from tests.conftest import register_and_login


def _user(outbox, email):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Измеримая цель"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def _verify(client, result_id, status="verified", rationale="Проверено, доказательства убедительны"):
    return client.post(
        f"/api/v1/results/{result_id}/verify",
        json={"status": status, "rationale": rationale},
    )


def test_criteria_and_measurements(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)

    criterion = owner.post(
        f"/api/v1/goals/{goal['id']}/criteria",
        json={
            "name": "Доля завершивших курс",
            "criterion_type": "quantitative",
            "baseline": "61%",
            "target_value": "78%",
            "unit": "%",
        },
    )
    assert criterion.status_code == 201, criterion.text

    for value in ("65%", "70%", "74%"):
        measurement = owner.post(
            f"/api/v1/criteria/{criterion.json()['id']}/measurements",
            json={"value": value, "source": "course analytics"},
        )
        assert measurement.status_code == 201

    listed = owner.get(f"/api/v1/goals/{goal['id']}/criteria")
    assert listed.json()[0]["target_value"] == "78%"

    stranger, _ = _user(outbox, "stranger@example.com")
    assert stranger.get(f"/api/v1/goals/{goal['id']}/criteria").status_code == 403


def test_result_flow_with_evidence_and_verification(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    verifier, verifier_user = _user(outbox, "verifier@example.com")
    goal = _goal(owner)

    # The verifier needs access to the goal to verify: invite as expert.
    owner.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": verifier_user["id"], "role": "expert"},
    )

    result = owner.post(
        f"/api/v1/goals/{goal['id']}/results",
        json={
            "description": "Доля завершивших курс выросла с 61% до 74%",
            "expected_state": "78% завершивших",
            "actual_state": "74% завершивших",
        },
    )
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "reported"
    result_id = result.json()["id"]

    evidence = owner.post(
        f"/api/v1/results/{result_id}/evidence",
        json={"evidence_type": "measurement", "content": "Analytics export 2026-09: 74.2% completion", "source": "stepik"},
    )
    assert evidence.status_code == 201

    listing = owner.get(f"/api/v1/goals/{goal['id']}/results")
    assert listing.json()[0]["evidence_count"] == 1


def test_reporter_cannot_verify_own_result(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    result = owner.post(
        f"/api/v1/goals/{goal['id']}/results",
        json={"description": "Результат собственного труда"},
    ).json()

    assert _verify(owner, result["id"]).status_code == 403


def test_verification_by_other_participant(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    verifier, verifier_user = _user(outbox, "verifier@example.com")
    goal = _goal(owner)
    owner.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": verifier_user["id"], "role": "expert"},
    )
    result = owner.post(
        f"/api/v1/goals/{goal['id']}/results",
        json={"description": "Курс опубликован и доступен"},
    ).json()

    verified = _verify(verifier, result["id"], "verified")
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    assert verified.json()["verified_at"] is not None

    # A verified result cannot be verified again.
    assert _verify(verifier, result["id"], "rejected").status_code == 409


def test_goal_achieved_requires_verified_result(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    verifier, verifier_user = _user(outbox, "verifier@example.com")
    goal = _goal(owner)
    owner.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": verifier_user["id"], "role": "expert"},
    )

    for action in ("propose", "accept", "activate"):
        assert owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": action}).status_code == 200

    # INV-3: no verified result -> cannot report the goal as achieved.
    response = owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": "report-achieved"})
    assert response.status_code == 409
    assert "verified result" in response.json()["detail"]

    # A merely reported (unverified) result is not enough either.
    owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Пока не проверено"})
    assert owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": "report-achieved"}).status_code == 409

    # Verified result unlocks the transition.
    result = owner.post(
        f"/api/v1/goals/{goal['id']}/results",
        json={"description": "Финальный результат"},
    ).json()
    assert _verify(verifier, result["id"]).status_code == 200
    achieved = owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": "report-achieved"})
    assert achieved.status_code == 200
    assert achieved.json()["status"] == "achieved"


def test_results_require_goal_access(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    assert stranger.post(
        f"/api/v1/goals/{goal['id']}/results",
        json={"description": "Чужой результат"},
    ).status_code == 403
