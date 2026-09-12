"""project_goals M2M and knowledge_relations (Track C7).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table(name: str, *columns, **kwargs) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(name):
        op.create_table(name, *columns, **kwargs)


def upgrade() -> None:
    _table(
        "project_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id"), nullable=False, index=True),
        sa.Column("relation_type", sa.String(30), nullable=False, server_default="serves"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "goal_id", name="uq_project_goal"),
    )
    _table(
        "knowledge_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_id", sa.Integer(), sa.ForeignKey("knowledge_items.id"), nullable=False, index=True),
        sa.Column("target_type", sa.String(20), nullable=False, index=True),
        sa.Column("target_id", sa.Integer(), nullable=False, index=True),
        sa.Column("relation_type", sa.String(30), nullable=False, server_default="supports"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("knowledge_id", "target_type", "target_id", name="uq_knowledge_relation"),
    )

    # Backfill: every legacy projects.goal_id becomes a project_goals row.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("project_goals"):
        bind.execute(sa.text(
            "INSERT INTO project_goals (project_id, goal_id, relation_type, created_by, created_at) "
            "SELECT id, goal_id, 'serves', owner_id, CURRENT_TIMESTAMP FROM projects "
            "WHERE goal_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM project_goals pg WHERE pg.project_id = projects.id AND pg.goal_id = projects.goal_id)"
        ))


def downgrade() -> None:
    op.drop_table("knowledge_relations")
    op.drop_table("project_goals")
