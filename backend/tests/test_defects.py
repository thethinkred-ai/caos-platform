"""Tests for the '10 defects' fixes (Track A of the improvement plan)."""

from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def _two_users(outbox):

    from app.main import app as main_app

    owner = TestClient(main_app)
    stranger = TestClient(main_app)
    owner_user = register_and_login(owner, outbox, email="owner@example.com", display_name="Owner")
    stranger_user = register_and_login(stranger, outbox, email="stranger@example.com", display_name="Stranger")
    return owner, stranger, owner_user, stranger_user


def _decision(owner, **extra):
    payload = {"title": "Решение о формате", "proposal": "Описание предложения", **extra}
    return owner.post("/api/v1/decisions", json=payload)


# A1: assignment requires project membership


def test_a1_assign_task_to_non_member_rejected(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D"}).json()
    task = owner.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "Task", "description": ""}).json()

    response = owner.patch(f"/api/v1/tasks/{task['id']}/assign", json={"assignee_id": stranger_user["id"]})
    assert response.status_code == 403
    assert "member" in response.json()["detail"].lower()


def test_a1_assign_task_to_member_allowed(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D"}).json()
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": stranger_user["id"], "role": "member"})
    task = owner.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "Task", "description": ""}).json()

    response = owner.patch(f"/api/v1/tasks/{task['id']}/assign", json={"assignee_id": stranger_user["id"]})
    assert response.status_code == 200


# A2: voting is limited to the goal context


def test_a2_stranger_cannot_vote_on_goal_decision(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель", "description": "D"}).json()
    decision = _decision(owner, goal_id=goal["id"]).json()

    response = stranger.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "reject"})
    assert response.status_code == 403


def test_a2_goal_participant_can_vote(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель", "description": "D"}).json()
    project = owner.post(
        "/api/v1/projects", json={"title": "Proj", "description": "D", "goal_id": goal["id"]}
    ).json()
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": stranger_user["id"], "role": "member"})
    decision = _decision(owner, goal_id=goal["id"]).json()

    assert stranger.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"}).status_code == 201
    finalized = owner.post(f"/api/v1/decisions/{decision['id']}/finalize")
    assert finalized.json()["status"] == "accepted"


def test_a2_standalone_decision_author_only(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    decision = _decision(owner).json()

    assert stranger.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"}).status_code == 403
    assert owner.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"}).status_code == 201


# A3: honest decision methods


def test_a3_invalid_method_rejected(client, outbox):
    owner, *_ = _two_users(outbox)
    response = _decision(owner, decision_method="consensus")
    assert response.status_code == 422
    response = _decision(owner, decision_method="banana")
    assert response.status_code == 422
    assert _decision(owner, decision_method="majority").status_code == 201
    assert _decision(owner, decision_method="unanimity").status_code == 201


def test_a3_unanimity_one_reject_rejects(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель", "description": "D"}).json()
    project = owner.post(
        "/api/v1/projects", json={"title": "Proj", "description": "D", "goal_id": goal["id"]}
    ).json()
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": stranger_user["id"], "role": "member"})
    decision = _decision(owner, goal_id=goal["id"], decision_method="unanimity", quorum=2).json()

    owner.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})
    stranger.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "reject"})
    finalized = owner.post(f"/api/v1/decisions/{decision['id']}/finalize")
    assert finalized.json()["status"] == "rejected"


# A4: AI retrieval is permission-scoped


def test_a4_ai_goal_endpoints_check_access(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Секретная цель", "description": "D"}).json()

    for path in (
        f"/api/v1/recommendations/decompose/{goal['id']}",
        f"/api/v1/recommendations/scenario/{goal['id']}",
        f"/api/v1/recommendations/risk-analysis/{goal['id']}",
        f"/api/v1/recommendations/goal-conflicts/{goal['id']}",
    ):
        assert stranger.get(path).status_code == 403, path
        assert owner.get(path).status_code == 200, path


def test_a4_similar_problems_do_not_leak_others(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    own = owner.post(
        "/api/v1/problems", json={"title": "Своя проблема про логику", "description": "d"}
    ).json()
    stranger.post(
        "/api/v1/problems", json={"title": "Чужая секретная проблема", "description": "d"}
    )

    response = owner.get(f"/api/v1/recommendations/similar-problems/{own['id']}")
    assert response.status_code == 200
    assert "секретная" not in response.json()["suggestion"].lower()


def test_a4_similar_problems_reject_foreign_problem(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    foreign = stranger.post(
        "/api/v1/problems", json={"title": "Чужая проблема", "description": "d"}
    ).json()
    assert owner.get(f"/api/v1/recommendations/similar-problems/{foreign['id']}").status_code == 403


def test_a4_knowledge_search_is_scoped(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    project = owner.post("/api/v1/projects", json={"title": "Proj", "description": "D"}).json()
    owner.post(
        "/api/v1/knowledge",
        json={"title": "Публичное знание владельца", "content": "c", "project_id": project["id"]},
    )
    stranger_project = stranger.post("/api/v1/projects", json={"title": "Proj2", "description": "D"}).json()
    stranger.post(
        "/api/v1/knowledge",
        json={"title": "Чужое секретное знание", "content": "c", "project_id": stranger_project["id"]},
    )

    response = owner.get("/api/v1/recommendations/knowledge", params={"q": "знание"})
    assert response.status_code == 200
    suggestion = response.json()["suggestion"]
    assert "секретное" not in suggestion.lower()


def test_a4_ai_status_does_not_leak_base_url(client, outbox):
    owner, *_ = _two_users(outbox)
    response = owner.get("/api/v1/ai/status")
    assert response.status_code == 200
    assert "base_url" not in response.json()


# A5: public profile has no email


def test_a5_profile_of_other_user_has_no_email(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    stranger.patch("/api/v1/profile/visibility", params={"visibility": "public"})

    response = owner.get(f"/api/v1/profile/{stranger_user['id']}")
    assert response.status_code == 200
    assert "email" not in response.json()["user"]

    own = owner.get(f"/api/v1/profile/{owner_user['id']}")
    assert own.json()["user"]["email"] == "owner@example.com"


# A6: vote aggregation instead of identifiable list


def test_a6_vote_aggregates_hide_voters_until_finalized(client, outbox):
    owner, stranger, owner_user, stranger_user = _two_users(outbox)
    goal = owner.post("/api/v1/goals", json={"title": "Цель", "description": "D"}).json()
    project = owner.post(
        "/api/v1/projects", json={"title": "Proj", "description": "D", "goal_id": goal["id"]}
    ).json()
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": stranger_user["id"], "role": "member"})
    decision = _decision(owner, goal_id=goal["id"], quorum=2).json()

    owner.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})
    stranger.post(f"/api/v1/decisions/{decision['id']}/vote", json={"variant": "accept"})

    votes = owner.get(f"/api/v1/decisions/{decision['id']}/votes").json()
    assert votes["accept"] == 2 and votes["total"] == 2 and votes["quorum_met"] is True
    assert votes["votes"] is None  # no identifiable list while open
    assert votes["own_vote"]["variant"] == "accept"

    owner.post(f"/api/v1/decisions/{decision['id']}/finalize")
    votes = owner.get(f"/api/v1/decisions/{decision['id']}/votes").json()
    assert votes["votes"] is not None and len(votes["votes"]) == 2


# A7: link creation verifies access


def test_a7_goal_cannot_reference_foreign_problem(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    foreign_problem = stranger.post(
        "/api/v1/problems", json={"title": "Чужая проблема", "description": "d"}
    ).json()

    response = owner.post(
        "/api/v1/goals",
        json={"title": "Цель", "description": "D", "problem_id": foreign_problem["id"]},
    )
    assert response.status_code == 403


def test_a7_goal_cannot_use_foreign_parent(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    foreign_goal = stranger.post("/api/v1/goals", json={"title": "Чужая цель", "description": "D"}).json()

    response = owner.post(
        "/api/v1/goals",
        json={"title": "Цель", "description": "D", "parent_goal_id": foreign_goal["id"]},
    )
    assert response.status_code == 403


def test_a7_project_cannot_reference_foreign_goal(client, outbox):
    owner, stranger, *_ = _two_users(outbox)
    foreign_goal = stranger.post("/api/v1/goals", json={"title": "Чужая цель", "description": "D"}).json()

    response = owner.post(
        "/api/v1/projects",
        json={"title": "Proj", "description": "D", "goal_id": foreign_goal["id"]},
    )
    assert response.status_code == 403
