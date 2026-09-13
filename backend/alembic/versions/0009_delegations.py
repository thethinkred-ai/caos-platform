"""delegations: bounded, time-limited capability transfers (Track H1, INV-7).

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("delegations"):
        op.create_table(
            "delegations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
            sa.Column("issuer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("capability", sa.String(30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("valid_from", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("valid_until", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("delegations")
