"""indexes on goals.deadline and tasks.deadline (overdue queries).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_goals_deadline", "goals", ["deadline"], if_not_exists=True)
    op.create_index("ix_tasks_deadline", "tasks", ["deadline"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_goals_deadline", table_name="goals")
    op.drop_index("ix_tasks_deadline", table_name="tasks")
