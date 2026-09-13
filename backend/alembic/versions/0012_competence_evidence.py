"""competence_evidence: practice-based competence proof (Step 30).

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("competence_evidence"):
        op.create_table(
            "competence_evidence",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("competence_id", sa.Integer(), sa.ForeignKey("competences.id"), nullable=False, index=True),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("competence_evidence")
