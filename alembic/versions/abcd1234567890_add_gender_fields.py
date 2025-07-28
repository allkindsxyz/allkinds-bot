"""add gender and looking_for fields

Revision ID: abcd1234567890_add_gender_fields  
Revises: f9a94676357a
Create Date: 2024-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abcd1234567890_add_gender_fields'
down_revision: Union[str, None] = 'f9a94676357a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gender and looking_for columns to group_members table
    op.add_column('group_members', sa.Column('gender', sa.String(length=16), nullable=True))
    op.add_column('group_members', sa.Column('looking_for', sa.String(length=16), nullable=True))


def downgrade() -> None:
    # Remove gender and looking_for columns from group_members table
    op.drop_column('group_members', 'looking_for')
    op.drop_column('group_members', 'gender') 