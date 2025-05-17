"""add country to group_members

Revision ID: ce1234567890
Revises: ce69890cf3a1
Create Date: 2025-05-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ce1234567890'
down_revision: Union[str, None] = 'ce69890cf3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('group_members', sa.Column('country', sa.String(length=128), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('group_members', 'country') 