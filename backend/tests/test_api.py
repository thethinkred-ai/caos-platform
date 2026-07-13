import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "caos_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_create_problem() -> None:
    email = "test@example.com"
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123", "display_name": "Tester"})
    assert response.status_code == 201
    token = response.json()["access_token"]
    response = client.post(
        "/api/v1/problems",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Create a local study group", "description": "Find two people and meet weekly."},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "open"

    goal = client.post(
        "/api/v1/goals",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Launch a study group", "description": "Create a measurable weekly study format."},
    )
    assert goal.status_code == 201
    decision = client.post(
        "/api/v1/decisions",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Accept study format", "proposal": "Use a weekly public session.", "goal_id": goal.json()["id"]},
    )
    assert decision.status_code == 201
    decision_id = decision.json()["id"]
    decision_event = client.post(
        f"/api/v1/decisions/{decision_id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "accepted", "content": "The proposal meets the goal criteria."},
    )
    assert decision_event.status_code == 201
    assert client.get(f"/api/v1/decisions/{decision_id}/events", headers={"Authorization": f"Bearer {token}"}).json()[0]["event_type"] == "proposal"

    second_user = client.post("/api/v1/auth/register", json={"email": "member@example.com", "password": "password123", "display_name": "Member"})
    assert second_user.status_code == 201
    second_user_id = second_user.json()["user"]["id"]

    team = client.post(
        "/api/v1/teams",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Study team", "description": "Weekly coordination."},
    )
    assert team.status_code == 201
    team_id = team.json()["id"]
    member = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": second_user_id},
    )
    assert member.status_code == 201

    project = client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Shared project", "description": "Deliver a first result."},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    project_member = client.post(
        f"/api/v1/projects/{project_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": second_user_id},
    )
    assert project_member.status_code == 201
    second_token = second_user.json()["access_token"]
    task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"title": "First shared task", "description": "Prepare the first step."},
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    completed = client.patch(
        f"/api/v1/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"


def test_search() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "search@example.com", "password": "password123", "display_name": "Searcher"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/problems", headers=h, json={"title": "Study group logistics", "description": "Coordinate weekly meetings."})
    client.post("/api/v1/knowledge", headers=h, json={"title": "Study methodology", "content": "How to run effective study sessions."})
    client.post("/api/v1/decisions", headers=h, json={"title": "Study format decision", "proposal": "Switch to weekly study circles."})
    results = client.get("/api/v1/search?q=study", headers=h)
    assert results.status_code == 200
    assert len(results.json()["problems"]) >= 1
    assert len(results.json()["knowledge"]) >= 1
    assert len(results.json()["decisions"]) >= 1


def test_knowledge_and_audit() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "know@example.com", "password": "password123", "display_name": "Knower"}).json()["access_token"]
    item = client.post("/api/v1/knowledge", headers={"Authorization": f"Bearer {token}"}, json={"title": "Best practices for study groups", "content": "Meet weekly, rotate facilitation."})
    assert item.status_code == 201
    assert item.json()["title"] == "Best practices for study groups"
    items = client.get("/api/v1/knowledge", headers={"Authorization": f"Bearer {token}"})
    assert items.status_code == 200
    assert len(items.json()) >= 1


def test_profile_update() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "profile@example.com", "password": "password123", "display_name": "Profiler"}).json()["access_token"]
    updated = client.patch("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, json={"display_name": "Updated Name", "bio": "Community organizer."})
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated Name"
    assert updated.json()["bio"] == "Community organizer."


def test_next_action() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "next@example.com", "password": "password123", "display_name": "Nexter"}).json()["access_token"]
    action = client.get("/api/v1/next-action", headers={"Authorization": f"Bearer {token}"})
    assert action.status_code == 200
    assert "label" in action.json()
    assert action.json()["section"] == "problems"


def test_ai_stub() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "ai@example.com", "password": "password123", "display_name": "AI User"}).json()["access_token"]
    problem = client.post("/api/v1/problems", headers={"Authorization": f"Bearer {token}"}, json={"title": "Find study partners", "description": "Need people for a math study group."})
    rec = client.get(f"/api/v1/recommendations/similar-problems/{problem.json()['id']}", headers={"Authorization": f"Bearer {token}"})
    assert rec.status_code == 200
    assert "suggestion" in rec.json()
    knowledge_rec = client.get("/api/v1/recommendations/knowledge?q=study", headers={"Authorization": f"Bearer {token}"})
    assert knowledge_rec.status_code == 200


def test_notifications() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "notif@example.com", "password": "password123", "display_name": "Notif"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    notifs = client.get("/api/v1/notifications", headers=h)
    assert notifs.status_code == 200
    assert notifs.json() == []


def test_goal_decomposition() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "decomp@example.com", "password": "password123", "display_name": "Decomposer"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    parent = client.post("/api/v1/goals", headers=h, json={"title": "Parent goal", "description": "Top-level objective."})
    assert parent.status_code == 201
    parent_id = parent.json()["id"]
    child = client.post("/api/v1/goals", headers=h, json={"title": "Sub-goal", "description": "Decomposed part.", "parent_goal_id": parent_id})
    assert child.status_code == 201
    assert child.json()["parent_goal_id"] == parent_id
    sub_goals = client.get(f"/api/v1/goals/{parent_id}/sub-goals", headers=h)
    assert sub_goals.status_code == 200
    assert len(sub_goals.json()) >= 1


def test_project_status_transition() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "status@example.com", "password": "password123", "display_name": "Statuser"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/v1/projects", headers=h, json={"title": "Status project", "description": "Test status transitions."})
    assert project.status_code == 201
    project_id = project.json()["id"]
    assert project.json()["status"] == "planned"
    active = client.patch(f"/api/v1/projects/{project_id}/status", headers=h, json={"status": "active"})
    assert active.status_code == 200
    assert active.json()["status"] == "active"
    completed = client.patch(f"/api/v1/projects/{project_id}/status", headers=h, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    invalid = client.patch(f"/api/v1/projects/{project_id}/status", headers=h, json={"status": "bogus"})
    assert invalid.status_code == 422


def test_notification_generation() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "notifgen@example.com", "password": "password123", "display_name": "NotifGen"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    decision = client.post("/api/v1/decisions", headers=h, json={"title": "Test decision", "proposal": "Proposal text."})
    decision_id = decision.json()["id"]
    client.post(f"/api/v1/decisions/{decision_id}/events", headers=h, json={"event_type": "accepted", "content": "Looks good."})
    notifs = client.get("/api/v1/notifications", headers=h)
    assert notifs.status_code == 200
    assert len(notifs.json()) >= 1
    assert "decision" in notifs.json()[0]["entity_type"]
    notif_id = notifs.json()[0]["id"]
    read = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=h)
    assert read.status_code == 200
    assert read.json()["is_read"] is True


def test_audit_listing() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "audit@example.com", "password": "password123", "display_name": "Auditor"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/knowledge", headers=h, json={"title": "Audit test knowledge", "content": "Testing audit trail."})
    audit = client.get("/api/v1/audit", headers=h)
    assert audit.status_code == 200
    assert len(audit.json()) >= 1
    assert audit.json()[0]["entity_type"] == "knowledge"


def test_competences() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "comp@example.com", "password": "password123", "display_name": "Competent"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/competences", headers=h, json={"name": "Facilitation", "level": 3, "description": "Weekly study group facilitation."})
    assert created.status_code == 201
    assert created.json()["name"] == "Facilitation"
    assert created.json()["level"] == 3
    listed = client.get("/api/v1/competences", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
    comp_id = created.json()["id"]
    deleted = client.delete(f"/api/v1/competences/{comp_id}", headers=h)
    assert deleted.status_code == 204
    after = client.get("/api/v1/competences", headers=h)
    assert len(after.json()) == 0


def test_knowledge_by_project() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "kp@example.com", "password": "password123", "display_name": "KP"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/v1/projects", headers=h, json={"title": "KP project", "description": "For knowledge linking."})
    project_id = project.json()["id"]
    client.post("/api/v1/knowledge", headers=h, json={"title": "Project lesson", "content": "What we learned.", "project_id": project_id})
    client.post("/api/v1/knowledge", headers=h, json={"title": "General knowledge", "content": "Not linked."})
    linked = client.get(f"/api/v1/knowledge?project_id={project_id}", headers=h)
    assert linked.status_code == 200
    assert len(linked.json()) == 1
    assert linked.json()[0]["project_id"] == project_id
    all_knowledge = client.get("/api/v1/knowledge", headers=h)
    assert len(all_knowledge.json()) >= 2


def test_task_assignment() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "assign@example.com", "password": "password123", "display_name": "Assigner"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/v1/projects", headers=h, json={"title": "Assign project", "description": "For task assignment."})
    project_id = project.json()["id"]
    task = client.post(f"/api/v1/projects/{project_id}/tasks", headers=h, json={"title": "Do something", "description": "Important task."})
    task_id = task.json()["id"]
    assert task.json()["assignee_id"] is None
    user_id = client.get("/api/v1/auth/me", headers=h).json()["id"]
    assigned = client.patch(f"/api/v1/tasks/{task_id}/assign", headers=h, json={"assignee_id": user_id})
    assert assigned.status_code == 200
    assert assigned.json()["assignee_id"] == user_id
    tasks = client.get(f"/api/v1/projects/{project_id}/tasks", headers=h)
    assert tasks.status_code == 200
    assert tasks.json()[0]["assignee_name"] == "Assigner"
    unassign = client.patch(f"/api/v1/tasks/{task_id}/assign", headers=h, json={"assignee_id": None})
    assert unassign.status_code == 200
    assert unassign.json()["assignee_id"] is None


def test_project_knowledge_count() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "pkc@example.com", "password": "password123", "display_name": "PKC"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/v1/projects", headers=h, json={"title": "PKC project", "description": "Knowledge count test."})
    project_id = project.json()["id"]
    assert project.json()["knowledge_count"] == 0
    client.post("/api/v1/knowledge", headers=h, json={"title": "Lesson 1", "content": "First.", "project_id": project_id})
    client.post("/api/v1/knowledge", headers=h, json={"title": "Lesson 2", "content": "Second.", "project_id": project_id})
    projects = client.get("/api/v1/projects", headers=h)
    found = [p for p in projects.json() if p["id"] == project_id][0]
    assert found["knowledge_count"] == 2


def test_ai_status_and_stub_fallback() -> None:
    token = client.post("/api/v1/auth/register", json={"email": "aistatus@example.com", "password": "password123", "display_name": "AIStatus"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    status_resp = client.get("/api/v1/ai/status", headers=h)
    assert status_resp.status_code == 200
    assert status_resp.json()["llm_available"] is False
    assert status_resp.json()["model"] is None
    problem = client.post("/api/v1/problems", headers=h, json={"title": "AI test problem", "description": "For AI stub test."})
    problem_id = problem.json()["id"]
    rec = client.get(f"/api/v1/recommendations/similar-problems/{problem_id}", headers=h)
    assert rec.status_code == 200
    assert rec.json()["source"] in ("keyword-match", "stub", "heuristic")
    assert rec.json()["confidence"] < 0.5
