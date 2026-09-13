"""Challenges and decision-process tests (Track C6) + the executable
invariant contract (Track E2)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Оспариваемая цель"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def _challenge(client, target_type, target_id, claim="Формулировка не проверяема"):
    return client.post(
        "/api/v1/challenges",
        json={
            "target_type": target_type,
            "target_id": target_id,
            "claim": claim,
            "argument": "Нет базовой линии и метрики, цель нельзя проверить",
            "alternative": "Добавить критерий с измеримым значением",
        },
    )


# --- C6: challenges ---


def test_challenge_goal_full_lifecycle(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    challenger, _ = _user(outbox, "challenger@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": challenger.get("/api/v1/auth/me").json()["id"], "role": "expert"})

    created = _challenge(challenger, "goal", goal["id"])
    assert created.status_code == 201, created.text
    challenge_id = created.json()["id"]
    assert created.json()["status"] == "open"

    listed = owner.get("/api/v1/challenges", params={"target_type": "goal", "target_id": goal["id"]})
    assert [c["id"] for c in listed.json()] == [challenge_id]

    # Only the challenged counterpart (goal owner) or the author may resolve.
    stranger, _ = _user(outbox, "stranger@example.com")
    assert stranger.post(
        f"/api/v1/challenges/{challenge_id}/resolve",
        json={"status": "rejected", "resolution": "нет"},
    ).status_code == 403

    resolved = owner.post(
        f"/api/v1/challenges/{challenge_id}/resolve",
        json={"status": "accepted", "resolution": "Критерий добавлен, формулировка уточнена"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "accepted"
    assert resolved.json()["resolved_at"] is not None

    # A resolved challenge is final.
    again = owner.post(
        f"/api/v1/challenges/{challenge_id}/resolve",
        json={"status": "rejected", "resolution": "передумали"},
    )
    assert again.status_code == 409
    assert again.json()["code"] == "CHALLENGE_ALREADY_RESOLVED"


def test_challenge_requires_target_access(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    assert _challenge(stranger, "goal", goal["id"]).status_code == 403


def test_author_can_withdraw_own_challenge(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    challenger, challenger_user = _user(outbox, "challenger@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": challenger_user["id"]})
    challenge = _challenge(challenger, "goal", goal["id"]).json()

    withdrawn = challenger.post(
        f"/api/v1/challenges/{challenge['id']}/resolve",
        json={"status": "withdrawn", "resolution": "Вопрос снят после обсуждения"},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"


def test_challenge_on_decision_and_result(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": member_user["id"]})

    decision = owner.post(
        "/api/v1/decisions",
        json={"title": "Спорное решение", "proposal": "Сократить программу", "goal_id": goal["id"]},
    ).json()
    assert _challenge(member, "decision", decision["id"]).status_code == 201

    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Результат под вопросом"}).json()
    assert _challenge(member, "result", result["id"]).status_code == 201


# --- C6: decision process ---


def test_decision_event_types_whitelisted(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    decision = owner.post("/api/v1/decisions", json={"title": "Решение", "proposal": "Текст"}).json()

    ok = owner.post(
        f"/api/v1/decisions/{decision['id']}/events",
        json={"event_type": "argument", "content": "Аргумент против"},
    )
    assert ok.status_code == 201
    bad = owner.post(
        f"/api/v1/decisions/{decision['id']}/events",
        json={"event_type": "harness", "content": "Что угодно"},
    )
    assert bad.status_code == 422
    # Frontend's legacy types still work.
    for legacy in ("accepted", "rejected", "revised", "comment"):
        assert owner.post(
            f"/api/v1/decisions/{decision['id']}/events",
            json={"event_type": legacy, "content": f"{legacy} content"},
        ).status_code == 201


def test_proposal_versions_created(client, outbox):
    from sqlalchemy import select

    from app.models import ProposalVersion
    from tests.conftest import TestingSessionLocal

    owner, _ = _user(outbox, "owner@example.com")
    decision = owner.post("/api/v1/decisions", json={"title": "Версионируемое", "proposal": "Версия один"}).json()

    owner.post(
        f"/api/v1/decisions/{decision['id']}/events",
        json={"event_type": "revision", "content": "Версия два после возражения"},
    )

    db = TestingSessionLocal()
    versions = list(db.scalars(
        select(ProposalVersion).where(ProposalVersion.decision_id == decision["id"]).order_by(ProposalVersion.version)
    ))
    db.close()
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].content == "Версия один"
    assert versions[1].content == "Версия два после возражения"


def test_supermajority_and_consent_methods(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    goal = _goal(owner, "Цель для решений")

    # supermajority: 2 of 3 is below 2/3 threshold? 2*3=6 >= 3*2=6 -> passes.
    # Use 1 of 3: 3 >= 6 false -> rejected.
    voters = []
    for i in range(3):
        voter, voter_user = _user(outbox, f"voter{i}@example.com")
        owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": voter_user["id"]})
        voters.append((voter, voter_user))

    decision = owner.post(
        "/api/v1/decisions",
        json={
            "title": "Супербольшинство", "proposal": "P", "goal_id": goal["id"],
            "decision_method": "supermajority", "quorum": 3,
        },
    ).json()

    voters[0][0].post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})
    voters[1][0].post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "reject"})
    voters[2][0].post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "reject"})
    finalized = owner.post(f"/api/v1/decisions/{decision['id']}/finalize")
    assert finalized.json()["status"] == "rejected"  # 1/3 accept < 2/3

    # consent: one reject blocks everything.
    consent_decision = owner.post(
        "/api/v1/decisions",
        json={
            "title": "Консент", "proposal": "P", "goal_id": goal["id"],
            "decision_method": "consent", "quorum": 2,
        },
    ).json()
    voters[0][0].post(f"/api/v1/decisions/{consent_decision['id']}/vote", json={"variant": "accept"})
    voters[1][0].post(f"/api/v1/decisions/{consent_decision['id']}/vote", json={"variant": "reject"})
    finalized = owner.post(f"/api/v1/decisions/{consent_decision['id']}/finalize")
    assert finalized.json()["status"] == "rejected"


def test_decision_cannot_reference_foreign_goal(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(stranger, "Чужая цель")
    response = owner.post(
        "/api/v1/decisions",
        json={"title": "Решение о чужой цели", "proposal": "P", "goal_id": goal["id"]},
    )
    assert response.status_code == 403


# --- E2: machine-readable error codes + executable invariant contract ---


def test_error_codes_present(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    response = owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": "activate"})
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"
    assert "detail" in response.json()  # frontend compatibility


def test_inv1_goal_cannot_skip_recognition(client, outbox):
    """INV-1: no goal becomes active without the recognition procedure."""
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    for skip in ("activate", "accept", "report-achieved"):
        response = owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": skip})
        assert response.status_code == 409, skip


def test_inv3_task_completion_is_not_goal_achievement(client, outbox):
    """INV-3: completing every task must not make the goal achievable."""
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    project = owner.post(
        "/api/v1/projects", json={"title": "Проект", "description": "D", "goal_id": goal["id"]}
    ).json()
    task = owner.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "Задача", "description": ""}).json()
    assert owner.patch(f"/api/v1/tasks/{task['id']}/complete").status_code == 200

    for action in ("propose", "accept", "activate"):
        owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": action})
    response = owner.post(f"/api/v1/goals/{goal['id']}/transition", json={"action": "report-achieved"})
    assert response.status_code == 409
    assert response.json()["code"] == "ACHIEVEMENT_REQUIRES_VERIFIED_RESULT"


def test_inv4_reporter_cannot_verify_own_result(client, outbox):
    """INV-4: a result is not verified because its reporter says so."""
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Свой результат"}).json()
    response = owner.post(
        f"/api/v1/results/{result['id']}/verify",
        json={"status": "verified", "rationale": "Сам проверил"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "SELF_VERIFICATION_FORBIDDEN"


def test_inv5_ai_is_read_only(client, outbox):
    """INV-5: no AI/recommendations route mutates domain state.

    The only allowed mutation is the human review of AI's own objects
    (resolving an ai_suggestion) — that IS the AI->Proposal->Human path.
    """
    _user(outbox, "owner@example.com")  # ensure app routes loaded
    mutating = {"POST", "PUT", "PATCH", "DELETE"}
    for route in app.routes:
        path = getattr(route, "path", "")
        is_ai_route = path.startswith("/api/v1/ai") or path.startswith("/api/v1/recommendations")
        if is_ai_route and hasattr(route, "methods"):
            if path.startswith("/api/v1/ai/suggestions"):
                continue
            assert not (route.methods & mutating), f"AI route mutates: {route.methods} {path}"


def test_inv11_graph_rejects_forbidden_cycles(client, outbox):
    """INV-11: the goal graph contains no forbidden cycles."""
    owner, _ = _user(outbox, "owner@example.com")
    a = _goal(owner, "Альфа")
    b = _goal(owner, "Бета")
    owner.post(f"/api/v1/goals/{a['id']}/relations", json={
        "target_goal_id": b["id"], "relation_type": "depends_on", "rationale": "Альфа ждёт Бету",
    })
    response = owner.post(f"/api/v1/goals/{b['id']}/relations", json={
        "target_goal_id": a["id"], "relation_type": "depends_on", "rationale": "Бета ждёт Альфу",
    })
    assert response.status_code == 400


def test_proposal_versions_listing_and_access(client, outbox):
    owner, _ = _user(outbox, "ver@example.com")
    member, member_user = _user(outbox, "vermember@example.com")
    goal = _goal(owner, "Цель с версиями")
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": member_user["id"]})

    decision = owner.post(
        "/api/v1/decisions",
        json={"title": "Версионированное решение", "proposal": "Первая редакция", "goal_id": goal["id"]},
    ).json()
    owner.post(
        f"/api/v1/decisions/{decision['id']}/events",
        json={"event_type": "revision", "content": "Вторая редакция"},
    )

    versions = owner.get(f"/api/v1/decisions/{decision['id']}/versions")
    assert versions.status_code == 200
    body = versions.json()
    assert [v["version"] for v in body] == [1, 2]
    assert body[0]["content"] == "Первая редакция"

    # A goal participant can read the versions; an outsider cannot.
    assert member.get(f"/api/v1/decisions/{decision['id']}/versions").status_code == 200
    stranger, _ = _user(outbox, "verstranger@example.com")
    assert stranger.get(f"/api/v1/decisions/{decision['id']}/versions").status_code == 403
