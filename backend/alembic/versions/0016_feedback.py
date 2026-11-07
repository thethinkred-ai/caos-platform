"""feedback: обратная связь пользователей и этап, на котором человек застрял.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("feedback"):
        op.create_table(
            "feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("page", sa.String(64), nullable=False, server_default=""),
            sa.Column("kind", sa.String(20), nullable=False, server_default="idea"),
            sa.Column("contact", sa.String(255), nullable=False, server_default=""),
            sa.Column("stage", sa.String(40), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="new"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_table("feedback")
