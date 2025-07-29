"""add banned_users table

Revision ID: add_banned_users_table
Revises: add_question_status_field
Create Date: 2025-01-28 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime


# revision identifiers, used by Alembic.
revision: str = 'add_banned_users_table'
down_revision: Union[str, None] = 'add_question_status_field'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create banned_users table
    op.create_table('banned_users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('banned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('banned_at', DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(255), server_default='Spam questions'),
        sa.UniqueConstraint('user_id', 'group_id', name='_banned_user_group_uc')
    )


def downgrade() -> None:
    # Drop banned_users table
    op.drop_table('banned_users') 