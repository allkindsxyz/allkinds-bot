"""add current_group_id to users

Revision ID: 68e2c55f8f13
Revises: 4e6981748778
Create Date: 2025-05-10 20:57:30.238516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68e2c55f8f13'
down_revision: Union[str, None] = '4e6981748778'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('current_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'groups', ['current_group_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'current_group_id')
    # ### end Alembic commands ###
