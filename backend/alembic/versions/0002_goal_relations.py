"""goal_relations: typed goal graph (ADR-0002, Track C1).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0001 converges dynamically to the CURRENT models, so on a fresh
    # database goal_relations may already exist by the time we get here.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("goal_relations"):
        return
    op.create_table(
        "goal_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
        sa.Column("target_goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_goal_id", "target_goal_id", "relation_type", name="uq_goal_relation"),
    )


def downgrade() -> None:
    op.drop_table("goal_relations")
