"""ai_suggestions evolve into AI proposals (Track G1): model, snapshot,
confidence, target and review metadata.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = (
    ("model_name", sa.String(100), False, ""),
    ("input_snapshot", sa.Text(), False, ""),
    ("confidence", sa.Float(), True, None),
    ("proposal_type", sa.String(30), False, "recommendation"),
    ("target_type", sa.String(20), False, ""),
    ("target_id", sa.Integer(), True, None),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {c["name"] for c in inspector.get_columns("ai_suggestions")}
    for name, col_type, nullable, default in _NEW_COLUMNS:
        if name not in existing:
            op.add_column("ai_suggestions", sa.Column(name, col_type, nullable=nullable, server_default=default))
    if "reviewed_by" not in existing:
        op.add_column("ai_suggestions", sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    if "reviewed_at" not in existing:
        op.add_column("ai_suggestions", sa.Column("reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for name, *_ in _NEW_COLUMNS:
        op.drop_column("ai_suggestions", name)
    op.drop_column("ai_suggestions", "reviewed_at")
    op.drop_column("ai_suggestions", "reviewed_by")
