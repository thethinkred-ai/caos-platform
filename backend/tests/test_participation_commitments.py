"""Participation and commitment tests (Track C3+C4)."""

from tests.conftest import register_and_login


def _user(outbox, email):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Общая цель"):
    response = client.post("/api/v1/goals", json={"title": title, "description": "Описание"})
    assert response.status_code == 201, response.text
    return response.json()


def _project_for(client, goal_id, title="Общий проект"):
    response = client.post("/api/v1/projects", json={"title": title, "description": "D", "goal_id": goal_id})
    assert response.status_code == 201, response.text
    return response.json()


# --- C3: participation ---


def test_join_via_project_membership(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")

    goal = _goal(owner)
    project = _project_for(owner, goal["id"])
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": member_user["id"], "role": "member"})

    # The member sees the goal through the project and explicitly joins it.
    joined = member.post(f"/api/v1/goals/{goal['id']}/participations", json={"role": "contributor"})
    assert joined.status_code == 201, joined.text
    assert joined.json()["role"] == "contributor"

    listed = owner.get(f"/api/v1/goals/{goal['id']}/participations")
    assert [p["user_id"] for p in listed.json()] == [member_user["id"]]


def test_participation_grants_access_without_project(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")

    goal = _goal(owner)
    project = _project_for(owner, goal["id"])

    # The member joins through the project access path...
    owner.post(f"/api/v1/projects/{project['id']}/members", json={"user_id": member_user["id"], "role": "member"})
    assert member.post(f"/api/v1/goals/{goal['id']}/participations", json={}).status_code == 201

    # ...and participation becomes an access path of its own: creating a
    # sub-goal under this goal works for the member.
    sub = member.post(
        "/api/v1/goals",
        json={"title": "Подцель участника", "description": "D", "parent_goal_id": goal["id"]},
    )
    assert sub.status_code == 201, sub.text


def test_stranger_cannot_join_private_goal(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    assert stranger.post(f"/api/v1/goals/{goal['id']}/participations", json={}).status_code == 403


def test_owner_invites_and_changes_role(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    invitee, invitee_user = _user(outbox, "invitee@example.com")
    goal = _goal(owner)

    invited = owner.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": invitee_user["id"], "role": "expert"},
    )
    assert invited.status_code == 201
    assert invited.json()["role"] == "expert"

    changed = owner.patch(f"/api/v1/goals/{goal['id']}/participations/{invitee_user['id']}", json={"role": "coordinator"})
    assert changed.status_code == 200
    assert changed.json()["role"] == "coordinator"

    # The invitee, now a participant, has access to the goal.
    assert invitee.get(f"/api/v1/goals/{goal['id']}/relations").status_code == 200


def test_leave_and_rejoin(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": member_user["id"], "role": "observer"})

    assert member.post(f"/api/v1/goals/{goal['id']}/participations/leave").status_code == 200
    listed = owner.get(f"/api/v1/goals/{goal['id']}/participations").json()
    assert listed[0]["status"] == "left"

    # Left participant loses the access path.
    assert member.get(f"/api/v1/goals/{goal['id']}/relations").status_code == 403

    # Re-join reactivates the same record (owner re-invites).
    reinvited = owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": member_user["id"]})
    assert reinvited.status_code == 201
    assert reinvited.json()["status"] == "active"


# --- C4: commitments ---


def test_commitment_flow_and_status_machine(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)

    created = owner.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Готовлю три урока к 1 октября", "expected_result": "Три опубликованных урока"},
    )
    assert created.status_code == 201, created.text
    commitment = created.json()
    assert commitment["status"] == "open"
    assert commitment["source"] == "self"

    # A commitment implies participation.
    participations = owner.get(f"/api/v1/goals/{goal['id']}/participations").json()
    assert participations and participations[0]["role"] == "contributor"

    # Status machine: open -> fulfilled directly is invalid.
    assert owner.post(f"/api/v1/commitments/{commitment['id']}/status", json={"status": "fulfilled"}).status_code == 409
    assert owner.post(f"/api/v1/commitments/{commitment['id']}/status", json={"status": "in_progress"}).status_code == 200
    assert owner.post(f"/api/v1/commitments/{commitment['id']}/status", json={"status": "fulfilled"}).status_code == 200

    mine = owner.get("/api/v1/commitments/my").json()
    assert [c["id"] for c in mine] == [commitment["id"]]
    assert mine[0]["status"] == "fulfilled"


def test_commitment_requires_goal_access(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    response = stranger.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Чужое обязательство"},
    )
    assert response.status_code == 403


def test_task_links_to_commitment(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    goal = _goal(owner)
    project = _project_for(owner, goal["id"])

    commitment = owner.post(
        f"/api/v1/goals/{goal['id']}/commitments",
        json={"description": "Делаю прототип"},
    ).json()

    task = owner.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Верстка прототипа", "description": "", "commitment_id": commitment["id"]},
    )
    assert task.status_code == 201, task.text
    assert task.json()["commitment_id"] == commitment["id"]

    # Linking to a nonexistent commitment fails.
    bad = owner.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Плохая задача", "description": "", "commitment_id": 99999},
    )
    assert bad.status_code == 404

    # Linking to someone else's commitment fails.
    stranger, _ = _user(outbox, "stranger@example.com")
    stranger_goal = _goal(stranger, "Чужая цель")
    stranger_commitment = stranger.post(
        f"/api/v1/goals/{stranger_goal['id']}/commitments",
        json={"description": "Не ваше дело"},
    ).json()
    foreign = owner.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Задача с чужим обязательством", "description": "", "commitment_id": stranger_commitment["id"]},
    )
    assert foreign.status_code == 403
