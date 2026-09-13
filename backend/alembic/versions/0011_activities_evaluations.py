"""activities and evaluations: the closing entities of the Step 18
ER model (Track D).

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("activities"):
        op.create_table(
            "activities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
            sa.Column("commitment_id", sa.Integer(), sa.ForeignKey("commitments.id"), nullable=True, index=True),
            sa.Column("activity_type", sa.String(30), nullable=False, server_default="task"),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="planned", index=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    if not inspector.has_table("evaluations"):
        op.create_table(
            "evaluations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("result_id", sa.Integer(), sa.ForeignKey("results.id"), nullable=False, index=True),
            sa.Column("evaluator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("conclusion", sa.String(40), nullable=False),
            sa.Column("insight", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("activities")
