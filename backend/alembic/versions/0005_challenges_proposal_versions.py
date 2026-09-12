"""challenges, proposal_versions, decisions.valid_until/review_at (Track C6).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("challenges"):
        op.create_table(
            "challenges",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("target_type", sa.String(20), nullable=False, index=True),
            sa.Column("target_id", sa.Integer(), nullable=False, index=True),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("claim", sa.Text(), nullable=False),
            sa.Column("argument", sa.Text(), nullable=False),
            sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
            sa.Column("alternative", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="open", index=True),
            sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
    if not inspector.has_table("proposal_versions"):
        op.create_table(
            "proposal_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("decision_id", sa.Integer(), sa.ForeignKey("decisions.id"), nullable=False, index=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    if "valid_until" not in decision_columns:
        op.add_column("decisions", sa.Column("valid_until", sa.DateTime(), nullable=True))
    if "review_at" not in decision_columns:
        op.add_column("decisions", sa.Column("review_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("decisions", "review_at")
    op.drop_column("decisions", "valid_until")
    op.drop_table("proposal_versions")
    op.drop_table("challenges")
