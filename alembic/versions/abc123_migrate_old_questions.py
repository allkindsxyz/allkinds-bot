"""migrate old questions to approved

Revision ID: abc123_migrate_old_questions
Revises: add_banned_users_table
Create Date: 2025-01-28 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123_migrate_old_questions'
down_revision: Union[str, None] = 'add_banned_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update all existing questions from 'pending' to 'approved' status
    # This is for backward compatibility - old questions created before moderation system
    # should be automatically approved since they were created without moderation
    op.execute("UPDATE questions SET status = 'approved' WHERE status = 'pending'")


def downgrade() -> None:
    # Revert all approved questions back to pending
    # Note: This will require manual admin approval again
    op.execute("UPDATE questions SET status = 'pending' WHERE status = 'approved'") 