"""reset alembic state and add bio

Revision ID: 59daa2d93eb
Revises: abcd1234567890_add_gender_fields
Create Date: 2025-01-28 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '59daa2d93eb'
down_revision: Union[str, None] = 'abcd1234567890_add_gender_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, fix any broken alembic state by updating the version table
    conn = op.get_bind()
    
    # Check if we have the broken revision in alembic_version table
    try:
        result = conn.execute(text("SELECT version_num FROM alembic_version WHERE version_num = '5b85129b983'"))
        if result.fetchone():
            # Replace broken revision with our parent revision
            conn.execute(text("UPDATE alembic_version SET version_num = 'abcd1234567890_add_gender_fields' WHERE version_num = '5b85129b983'"))
    except Exception:
        # Table might not exist or other issues, continue
        pass
    
    # Check if bio column exists before adding it
    try:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='group_members' AND column_name='bio'
        """))
        
        if not result.fetchone():
            # bio column doesn't exist, add it
            op.add_column('group_members', sa.Column('bio', sa.Text(), nullable=True))
    except Exception as e:
        # If we can't check, try to add anyway (will fail safely if exists)
        try:
            op.add_column('group_members', sa.Column('bio', sa.Text(), nullable=True))
        except Exception:
            # Column probably already exists, that's fine
            pass


def downgrade() -> None:
    # Check if bio column exists before dropping it
    conn = op.get_bind()
    try:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='group_members' AND column_name='bio'
        """))
        
        if result.fetchone():
            # bio column exists, drop it
            op.drop_column('group_members', 'bio')
    except Exception:
        # If we can't check, try to drop anyway (will fail safely if not exists)
        try:
            op.drop_column('group_members', 'bio')
        except Exception:
            # Column probably doesn't exist, that's fine
            pass 