"""add status field to questions

Revision ID: add_question_status_field
Revises: abcd1234567890_add_gender_fields
Create Date: 2025-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_question_status_field'
down_revision: Union[str, None] = 'abcd1234567890_add_gender_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to questions table
    op.add_column('questions', sa.Column('status', sa.String(16), nullable=False, server_default='pending'))


def downgrade() -> None:
    # Remove status column from questions table
    op.drop_column('questions', 'status') 