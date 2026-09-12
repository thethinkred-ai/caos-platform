"""goal criteria, measurements, results, evidence, verifications (Track C5).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table(name: str, *columns) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(name):
        op.create_table(name, *columns)


def upgrade() -> None:
    _table(
        "goal_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("criterion_type", sa.String(20), nullable=False, server_default="quantitative"),
        sa.Column("baseline", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("unit", sa.String(50), nullable=False, server_default=""),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    _table(
        "goal_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("criterion_id", sa.Integer(), sa.ForeignKey("goal_criteria.id"), nullable=False, index=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("measured_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("source", sa.String(200), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
    )
    _table(
        "results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_state", sa.Text(), nullable=False, server_default=""),
        sa.Column("actual_state", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="reported", index=True),
        sa.Column("reported_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    _table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("results.id"), nullable=False, index=True),
        sa.Column("evidence_type", sa.String(30), nullable=False, server_default="document"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    _table(
        "verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("results.id"), nullable=False, index=True),
        sa.Column("verifier_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verifications")
    op.drop_table("evidence")
    op.drop_table("results")
    op.drop_table("goal_measurements")
    op.drop_table("goal_criteria")
