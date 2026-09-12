"""goal participations, commitments, tasks.commitment_id (Track C3+C4).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0001 converges dynamically to the CURRENT models, so on a fresh
    # database these tables/column may already exist by now.
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("goal_participations"):
        op.create_table(
            "goal_participations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("role", sa.String(30), nullable=False, server_default="contributor"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("left_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("goal_id", "user_id", name="uq_goal_participation"),
        )
    if not inspector.has_table("commitments"):
        op.create_table(
            "commitments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("expected_result", sa.Text(), nullable=False, server_default=""),
            sa.Column("deadline", sa.DateTime(), nullable=True),
            sa.Column("source", sa.String(20), nullable=False, server_default="self"),
            sa.Column("status", sa.String(20), nullable=False, server_default="open", index=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    task_columns = {c["name"] for c in inspector.get_columns("tasks")}
    if "commitment_id" not in task_columns:
        op.add_column("tasks", sa.Column("commitment_id", sa.Integer(), sa.ForeignKey("commitments.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "commitment_id")
    op.drop_table("commitments")
    op.drop_table("goal_participations")
