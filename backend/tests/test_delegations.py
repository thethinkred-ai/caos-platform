"""Delegation tests (Track H1): bounded, time-limited capability
transfers — the executable contract for invariant INV-7."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TestingSessionLocal, register_and_login


def _user(outbox, email):
    client = TestClient(app)
    user = register_and_login(client, outbox, email=email, display_name=email.split("@")[0].title())
    return client, user


def _goal(client, title="Цель с делегированием"):
    return client.post("/api/v1/goals", json={"title": title, "description": "D"}).json()


def _delegate(owner, goal_id, recipient_id, capability="coordinate", hours=24, reason="Отпуск координатора"):
    return owner.post(
        f"/api/v1/goals/{goal_id}/delegations",
        json={
            "recipient_id": recipient_id,
            "capability": capability,
            "reason": reason,
            "valid_until": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
        },
    )


def test_owner_delegates_coordinate_and_recipient_gains_power(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    delegate, delegate_user = _user(outbox, "delegate@example.com")
    newcomer, newcomer_user = _user(outbox, "newcomer@example.com")
    goal = _goal(owner)

    created = _delegate(owner, goal["id"], delegate_user["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["capability"] == "coordinate"
    assert body["revoked_at"] is None

    # The delegate can now do a coordinate action: invite a third person.
    invited = delegate.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": newcomer_user["id"], "role": "observer"},
    )
    assert invited.status_code == 201, invited.text


def test_only_holder_can_delegate(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner)
    owner.post(f"/api/v1/goals/{goal['id']}/participations", json={"user_id": member_user["id"]})

    # A contributor does not hold 'coordinate' and cannot delegate it.
    response = _delegate(member, goal["id"], 999)
    assert response.status_code == 403


def test_recognize_is_not_delegatable(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    member, member_user = _user(outbox, "member@example.com")
    goal = _goal(owner)
    response = _delegate(owner, goal["id"], member_user["id"], capability="recognize")
    assert response.status_code == 422


def test_validation_self_and_past_expiry(client, outbox):
    owner, owner_user = _user(outbox, "owner@example.com")
    goal = _goal(owner)

    self_gift = _delegate(owner, goal["id"], owner_user["id"])
    assert self_gift.status_code == 422

    past = owner.post(
        f"/api/v1/goals/{goal['id']}/delegations",
        json={
            "recipient_id": owner_user["id"],
            "capability": "coordinate",
            "reason": "прошедший срок",
            "valid_until": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        },
    )
    assert past.status_code == 422


def test_revoke_is_faster_than_grant(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    delegate, delegate_user = _user(outbox, "delegate@example.com")
    newcomer, newcomer_user = _user(outbox, "newcomer@example.com")
    goal = _goal(owner)

    delegation = _delegate(owner, goal["id"], delegate_user["id"]).json()

    # Revoked by the goal owner (not the issuer) — revocation is cheap.
    revoked = owner.post(f"/api/v1/delegations/{delegation['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None

    # The capability is gone immediately.
    denied = delegate.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": newcomer_user["id"], "role": "observer"},
    )
    assert denied.status_code == 403

    # Double revoke is a 409 with a coded error.
    again = owner.post(f"/api/v1/delegations/{delegation['id']}/revoke")
    assert again.status_code == 409


def test_inv7_expired_delegation_grants_nothing(client, outbox):
    """INV-7: an expired delegation must not grant the capability."""
    owner, _ = _user(outbox, "owner@example.com")
    delegate, delegate_user = _user(outbox, "delegate@example.com")
    goal = _goal(owner)

    # Insert an already-expired delegation directly (endpoint rejects it).
    db = TestingSessionLocal()
    from app.models import Delegation

    db.add(Delegation(
        goal_id=goal["id"], issuer_id=owner.get("/api/v1/auth/me").json()["id"],
        recipient_id=delegate_user["id"], capability="coordinate",
        reason="истёкшее", valid_from=datetime.now(UTC) - timedelta(days=2),
        valid_until=datetime.now(UTC) - timedelta(days=1),
    ))
    db.commit()
    db.close()

    newcomer, newcomer_user = _user(outbox, "late@example.com")
    denied = delegate.post(
        f"/api/v1/goals/{goal['id']}/participations",
        json={"user_id": newcomer_user["id"], "role": "observer"},
    )
    assert denied.status_code == 403


def test_stranger_cannot_revoke_foreign_delegation(client, outbox):
    owner, _ = _user(outbox, "owner@example.com")
    delegate, delegate_user = _user(outbox, "delegate@example.com")
    stranger, _ = _user(outbox, "stranger@example.com")
    goal = _goal(owner)
    delegation = _delegate(owner, goal["id"], delegate_user["id"]).json()

    assert stranger.post(f"/api/v1/delegations/{delegation['id']}/revoke").status_code == 403
