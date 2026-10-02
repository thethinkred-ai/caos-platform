"""goals.deadline and tasks.deadline (ontology: a goal has a time bound).

The critique's Step 18 ontology always specified a goal deadline; the
bot audit of 02.10.2026 confirmed it was missing from the schema.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column(table: str, inspector) -> None:
    columns = {c["name"] for c in inspector.get_columns(table)}
    if "deadline" not in columns:
        op.add_column(table, sa.Column("deadline", sa.DateTime(), nullable=True))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _add_column("goals", inspector)
    _add_column("tasks", inspector)


def downgrade() -> None:
    op.drop_column("tasks", "deadline")
    op.drop_column("goals", "deadline")
