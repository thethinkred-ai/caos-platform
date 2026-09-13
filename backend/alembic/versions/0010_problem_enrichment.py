"""problem enrichment (current_state, scope) and problem_versions
(Track D, Step 18 of the critique).

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("problem_versions"):
        op.create_table(
            "problem_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id"), nullable=False, index=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("current_state", sa.Text(), nullable=False, server_default=""),
            sa.Column("scope", sa.Text(), nullable=False, server_default=""),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    problem_columns = {c["name"] for c in inspector.get_columns("problems")}
    if "current_state" not in problem_columns:
        op.add_column("problems", sa.Column("current_state", sa.Text(), nullable=False, server_default=""))
    if "scope" not in problem_columns:
        op.add_column("problems", sa.Column("scope", sa.Text(), nullable=False, server_default=""))

    # Backfill v1 for problems that have no version history yet. On a
    # fresh database (new schema from 0001) this is a no-op for rows
    # created via the API - those get v1 at creation time.
    if inspector.has_table("problem_versions"):
        bind.execute(sa.text(
            "INSERT INTO problem_versions (problem_id, version, title, description, current_state, scope, author_id, created_at) "
            "SELECT p.id, 1, p.title, p.description, p.current_state, p.scope, p.author_id, p.created_at FROM problems p "
            "WHERE NOT EXISTS (SELECT 1 FROM problem_versions pv WHERE pv.problem_id = p.id)"
        ))


def downgrade() -> None:
    op.drop_table("problem_versions")
    op.drop_column("problems", "scope")
    op.drop_column("problems", "current_state")
