"""Resources and goal export tests (external comment 03.10.2026)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Цель с ресурсами"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def test_resource_lifecycle_and_bottleneck(client, outbox):
    owner, _ = _user(outbox, "res@example.com")
    stranger, _ = _user(outbox, "resstranger@example.com")
    goal = _goal(owner)

    created = owner.post(
        f"/api/v1/goals/{goal['id']}/resources",
        json={
            "name": "Зал для занятий на 30 человек",
            "resource_type": "venue",
            "quantity": "1",
            "unit": "зал/нед",
            "is_critical": True,
        },
    )
    assert created.status_code == 201, created.text
    resource = created.json()
    assert resource["status"] == "required"

    labor = owner.post(
        f"/api/v1/goals/{goal['id']}/resources",
        json={"name": "Преподаватель логики", "resource_type": "labor"},
    )
    assert labor.status_code == 201

    # Stranger cannot add resources.
    assert stranger.post(
        f"/api/v1/goals/{goal['id']}/resources",
        json={"name": "Чужой ресурс", "resource_type": "other"},
    ).status_code == 403

    # A critical unsecured resource is a bottleneck in the impact.
    impact = owner.get(f"/api/v1/goals/{goal['id']}/impact").json()
    assert impact["critical_resources"] == 1

    secured = owner.patch(f"/api/v1/resources/{resource['id']}", json={"status": "secured"})
    assert secured.status_code == 200
    impact = owner.get(f"/api/v1/goals/{goal['id']}/impact").json()
    assert impact["critical_resources"] == 0

    # Resources appear in the explain chain.
    explain = owner.get(f"/api/v1/goals/{goal['id']}/explain").json()
    kinds = [n["kind"] for n in explain["chain"]]
    assert "resource" in kinds and explain["counts"]["resources"] == 2


def test_goal_export_markdown(client, outbox):
    owner, owner_user = _user(outbox, "exp@example.com")
    goal = _goal(owner, "Экспортируемая цель")
    owner.post(f"/api/v1/goals/{goal['id']}/criteria", json={"name": "Уроки", "target_value": "6"})
    owner.post(
        f"/api/v1/goals/{goal['id']}/resources",
        json={"name": "Критический зал", "resource_type": "venue", "is_critical": True},
    )
    cm = owner.post(f"/api/v1/goals/{goal['id']}/commitments", json={"description": "Пишу программу"}).json()
    result = owner.post(f"/api/v1/goals/{goal['id']}/results", json={"description": "Программа готова"}).json()

    exported = owner.get(f"/api/v1/goals/{goal['id']}/export")
    assert exported.status_code == 200
    assert "text/markdown" in exported.headers["content-type"]
    md = exported.text
    for fragment in [
        "# Экспортируемая цель",
        "## Критерии достижения",
        "## Ресурсы",
        "⚠️ критический",
        "## Обязательства",
        "Пишу программу",
        "## Результаты",
        "Экспортировано из CAOS",
    ]:
        assert fragment in md, fragment

    stranger, _ = _user(outbox, "expstranger@example.com")
    assert stranger.get(f"/api/v1/goals/{goal['id']}/export").status_code == 403
