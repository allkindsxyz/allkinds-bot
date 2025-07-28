"""fix bio field safe

Revision ID: 2498f9c5d6d
Revises: f22692de6fa
Create Date: 2025-01-28 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '2498f9c5d6d'
down_revision: Union[str, None] = 'abcd1234567890_add_gender_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if bio column exists before adding it
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='group_members' AND column_name='bio'
    """))
    
    if not result.fetchone():
        # bio column doesn't exist, add it
        op.add_column('group_members', sa.Column('bio', sa.Text(), nullable=True))


def downgrade() -> None:
    # Check if bio column exists before dropping it
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='group_members' AND column_name='bio'
    """))
    
    if result.fetchone():
        # bio column exists, drop it
        op.drop_column('group_members', 'bio') 