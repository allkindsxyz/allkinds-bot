"""remove is_admin from users

Revision ID: 5752bda3da04
Revises: 274a0e133760
Create Date: 2024-05-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5752bda3da04'
down_revision = '274a0e133760'
branch_labels = None
depends_on = None

def upgrade():
    op.drop_column('users', 'is_admin')

def downgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True, server_default=sa.text('false')))
