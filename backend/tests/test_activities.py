"""Activities and evaluations tests (Track D, Step 18 closure)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Цель с деятельностью"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def test_activity_types_and_status_machine(client, outbox):
    owner, _ = _user(outbox, "act@example.com")
    goal = _goal(owner)

    meeting = owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "meeting", "title": "Организационная встреча", "description": "Раздача ролей"},
    )
    assert meeting.status_code == 201, meeting.text
    body = meeting.json()
    assert body["status"] == "planned"

    research = owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "research", "title": "Анализ причин отсева"},
    )
    assert research.status_code == 201

    # Invalid type rejected.
    assert owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "party", "title": "Вечеринка"},
    ).status_code == 422

    activity_id = meeting.json()["id"]
    # Status machine: planned -> completed directly is invalid.
    assert owner.post(f"/api/v1/activities/{activity_id}/status", json={"status": "completed"}).status_code == 409
    assert owner.post(f"/api/v1/activities/{activity_id}/status", json={"status": "in_progress"}).status_code == 200
    done = owner.post(f"/api/v1/activities/{activity_id}/status", json={"status": "completed"})
    assert done.status_code == 200

    listed = owner.get(f"/api/v1/goals/{goal['id']}/activities")
    assert len(listed.json()) == 2
    assert listed.json()[0]["creator_name"] == "Act"


def test_activity_commitment_link_validated(client, outbox):
    owner, _ = _user(outbox, "actc@example.com")
    goal = _goal(owner)
    commitment = owner.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Готовлю программу"},
    ).json()
    foreign_goal = _goal(owner, "Другая цель")
    foreign_commitment = owner.post(
        f"/api/v1/goals/{foreign_goal['id']}/commitments",
        json={"description": "Чужое обязательство"},
    ).json()

    ok = owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "task", "title": "Составить программу", "commitment_id": commitment["id"]},
    )
    assert ok.status_code == 201

    # A commitment from another goal cannot be referenced.
    bad = owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "task", "title": "Некорректная связь", "commitment_id": foreign_commitment["id"]},
    )
    assert bad.status_code == 404


def test_evaluations_distinguish_meaning_from_fact(client, outbox):
    owner, _ = _user(outbox, "eval@example.com")
    evaluator, _ = _user(outbox, "evalee@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": evaluator.get("/api/v1/auth/me").json()["id"]})

    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Курс запущен"}).json()

    evaluation = evaluator.post(
        f"/api/v1/results/{result['id']}/evaluations",
        json={
            "conclusion": "partially_successful",
            "insight": "Курс запущен, но отсев на втором модуле не устранён - цель достигнута частично",
        },
    )
    assert evaluation.status_code == 201, evaluation.text

    bad = evaluator.post(
        f"/api/v1/results/{result['id']}/evaluations",
        json={"conclusion": "super", "insight": ""},
    )
    assert bad.status_code == 422

    listed = evaluator.get(f"/api/v1/results/{result['id']}/evaluations")
    assert listed.json()[0]["conclusion"] == "partially_successful"

    stranger, _ = _user(outbox, "evalstranger@example.com")
    assert stranger.get(f"/api/v1/results/{result['id']}/evaluations").status_code == 403


def test_explain_includes_activity_nodes(client, outbox):
    owner, _ = _user(outbox, "expl@example.com")
    goal = _goal(owner, "Цель для трассировки")
    owner.post(
        f"/api/v1/goals/{goal['id']}/activities",
        json={"activity_type": "research", "title": "Исследование отсева"},
    )

    explain = owner.get(f"/api/v1/goals/{goal['id']}/explain")
    kinds = [n["kind"] for n in explain.json()["chain"]]
    assert "activity" in kinds
    assert explain.json()["counts"]["activities"] == 1
