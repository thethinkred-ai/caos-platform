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
    op.add_column("decisions", sa.Column("ballot_secret", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("votes", sa.Column("voter_hash", sa.String(64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, decision_id, user_id FROM votes")).fetchall()
    for vote_id, decision_id, user_id in rows:
        digest = hmac.new(_secret(), f"{decision_id}:{user_id}".encode(), hashlib.sha256).hexdigest()
        bind.execute(
            sa.text("UPDATE votes SET voter_hash = :h WHERE id = :id"),
            {"h": digest, "id": vote_id},
        )

    with op.batch_alter_table("votes") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch.drop_constraint("uq_vote_decision_user", type_="unique")
        batch.create_unique_constraint("uq_vote_decision_voter", ["decision_id", "voter_hash"])
    op.create_index("ix_votes_voter_hash", "votes", ["voter_hash"])


def downgrade() -> None:
    with op.batch_alter_table("votes") as batch:
        batch.drop_constraint("uq_vote_decision_voter", type_="unique")
        batch.create_unique_constraint("uq_vote_decision_user", ["decision_id", "user_id"])
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("voter_hash")
    op.drop_column("decisions", "ballot_secret")
