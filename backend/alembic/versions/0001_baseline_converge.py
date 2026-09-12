"""Baseline: converge any existing database to the full model schema.

Creates missing tables and adds missing columns (nullable, backfilled,
then constrained) so that databases created by Base.metadata.create_all
at various points in history — which adds tables but never columns —
are brought up to date with app.models.

Revision ID: 0001
Revises:
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db import Base
import app.models  # noqa: F401  — register all models on Base.metadata

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _scalar_server_default(col: sa.Column):
    """Translate a Python-level scalar column default into a server default
    so that ADD COLUMN can backfill existing rows (SQLite-compatible)."""
    if col.server_default is not None:
        return None  # already present on the copy
    if col.default is None or not col.default.is_scalar:
        return None
    value = col.default.arg
    if value is True:
        return sa.true()
    if value is False:
        return sa.false()
    return sa.text(repr(value))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            table.create(bind, checkfirst=True)
            continue

        existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_columns:
                continue

            copy = col.copy()
            server_default = _scalar_server_default(col)
            was_nullable = col.nullable
            copy.nullable = True
            if server_default is not None:
                copy.server_default = server_default
            op.add_column(table.name, copy)

            # SQLite's ADD COLUMN ... DEFAULT does not backfill existing
            # rows (they stay NULL) — do it explicitly.
            if col.default is not None and col.default.is_scalar:
                op.execute(
                    sa.text(
                        f"UPDATE {table.name} SET {col.name} = :v WHERE {col.name} IS NULL"
                    ).bindparams(v=col.default.arg)
                )

            # Existing rows are backfilled by the server default. Enforce
            # NOT NULL directly on PostgreSQL; SQLite cannot ALTER a column
            # after creation, and batch-recreating tables is unsafe here —
            # the application itself always supplies a value (python-level
            # default), so the looser dev constraint is acceptable.
            if not was_nullable and not is_sqlite:
                op.alter_column(
                    table.name,
                    col.name,
                    nullable=False,
                    existing_type=col.type,
                    existing_server_default=server_default,
                )


def downgrade() -> None:
    # Convergence baseline: dropping down would destroy data on any
    # database that had tables before this migration.
    raise NotImplementedError("baseline convergence migration cannot be reverted")
