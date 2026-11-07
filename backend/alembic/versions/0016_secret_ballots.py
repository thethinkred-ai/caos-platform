"""votes: voter_hash pseudonymization and secret ballots.

Secret ballots (Decision.ballot_secret) store only
HMAC(secret, decision:user) instead of user_id - how a person voted is
not readable from a casual DB dump. Double-vote prevention moves to the
(decision_id, voter_hash) unique constraint; own-vote lookup recomputes
the hash. Open ballots keep user_id (transparency intended).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-18

"""
import hashlib
import hmac
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _secret() -> bytes:
    return (
        os.environ.get("VOTE_HASH_SECRET")
        or os.environ.get("JWT_SECRET")
        or "local-development-secret-change-me"
    ).encode()


def upgrade() -> None:
    # Базовая миграция 0001 сходяет любую БД к текущим моделям, поэтому на
    # чистой базе столбцы/констрейнты 0016 могут уже существовать - всё
    # добавляем только при отсутствии (как в 0013_deadlines).
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "ballot_secret" not in {c["name"] for c in inspector.get_columns("decisions")}:
        op.add_column("decisions", sa.Column("ballot_secret", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "voter_hash" not in {c["name"] for c in inspector.get_columns("votes")}:
        op.add_column("votes", sa.Column("voter_hash", sa.String(64), nullable=True))

    rows = bind.execute(sa.text("SELECT id, decision_id, user_id FROM votes WHERE voter_hash IS NULL")).fetchall()
    for vote_id, decision_id, user_id in rows:
        digest = hmac.new(_secret(), f"{decision_id}:{user_id}".encode(), hashlib.sha256).hexdigest()
        bind.execute(
            sa.text("UPDATE votes SET voter_hash = :h WHERE id = :id"),
            {"h": digest, "id": vote_id},
        )

    vote_cons = {c.get("name") for c in inspector.get_unique_constraints("votes")}
    user_id_nullable = next(
        (c["nullable"] for c in inspector.get_columns("votes") if c["name"] == "user_id"), True
    )
    with op.batch_alter_table("votes") as batch:
        if not user_id_nullable:
            batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        if "uq_vote_decision_user" in vote_cons:
            batch.drop_constraint("uq_vote_decision_user", type_="unique")
        if "uq_vote_decision_voter" not in vote_cons:
            batch.create_unique_constraint("uq_vote_decision_voter", ["decision_id", "voter_hash"])
    if "ix_votes_voter_hash" not in {i["name"] for i in inspector.get_indexes("votes")}:
        op.create_index("ix_votes_voter_hash", "votes", ["voter_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    vote_cons = {c.get("name") for c in inspector.get_unique_constraints("votes")}
    with op.batch_alter_table("votes") as batch:
        if "uq_vote_decision_voter" in vote_cons:
            batch.drop_constraint("uq_vote_decision_voter", type_="unique")
        if "uq_vote_decision_user" not in vote_cons:
            batch.create_unique_constraint("uq_vote_decision_user", ["decision_id", "user_id"])
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        if "voter_hash" in {c["name"] for c in inspector.get_columns("votes")}:
            batch.drop_column("voter_hash")
    if "ballot_secret" in {c["name"] for c in inspector.get_columns("decisions")}:
        op.drop_column("decisions", "ballot_secret")
