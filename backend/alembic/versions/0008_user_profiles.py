"""user_profiles: identity/profile separation (Track D2).

Display name and bio move from users into a 1:1 user_profiles table;
code keeps working through User.display_name / User.bio properties.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("user_profiles"):
        op.create_table(
            "user_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
            sa.Column("bio", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    # Backfill every existing user exactly once — only meaningful when
    # the legacy users columns still exist (fresh databases created by
    # 0001 already have the new schema).
    bind = op.get_bind()
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "display_name" in user_columns:
        bind.execute(sa.text(
            "INSERT INTO user_profiles (user_id, display_name, bio, created_at) "
            "SELECT id, display_name, bio, CURRENT_TIMESTAMP FROM users "
            "WHERE id NOT IN (SELECT user_id FROM user_profiles)"
        ))

    # Drop the moved columns (batch mode supports SQLite).
    if "display_name" in user_columns or "bio" in user_columns:
        with op.batch_alter_table("users") as batch:
            if "display_name" in user_columns:
                batch.drop_column("display_name")
            if "bio" in user_columns:
                batch.drop_column("bio")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("display_name", sa.String(120), nullable=False, server_default=""))
        batch.add_column(sa.Column("bio", sa.Text(), nullable=False, server_default=""))
    op.execute(sa.text(
        "UPDATE users SET display_name = (SELECT display_name FROM user_profiles WHERE user_profiles.user_id = users.id), "
        "bio = (SELECT bio FROM user_profiles WHERE user_profiles.user_id = users.id)"
    ))
    op.drop_table("user_profiles")
