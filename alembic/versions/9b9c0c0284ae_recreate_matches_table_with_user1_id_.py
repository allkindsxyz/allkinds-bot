"""recreate matches table with user1_id, user2_id, group_id, created_at, status, unique constraint

Revision ID: 9b9c0c0284ae
Revises: ce9999999999
Create Date: 2025-05-20 15:40:40.326269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b9c0c0284ae'
down_revision: Union[str, None] = 'ce9999999999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Безопасно: если таблицы нет, просто создаём
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user1_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user2_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
        sa.UniqueConstraint('user1_id', 'user2_id', 'group_id', name='_match_pair_uc'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('matches')
