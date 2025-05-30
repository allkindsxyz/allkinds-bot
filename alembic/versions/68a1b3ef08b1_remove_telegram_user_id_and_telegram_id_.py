"""remove telegram_user_id and telegram_id from users, truncate all user data

Revision ID: 68a1b3ef08b1
Revises: 
Create Date: 2025-05-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '68a1b3ef08b1'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # --- Drop columns from users ---
    with op.batch_alter_table('users') as batch_op:
        if 'telegram_user_id' in [c['name'] for c in op.get_bind().engine.dialect.get_columns(op.get_bind(), 'users')]:
            batch_op.drop_column('telegram_user_id')
        if 'telegram_id' in [c['name'] for c in op.get_bind().engine.dialect.get_columns(op.get_bind(), 'users')]:
            batch_op.drop_column('telegram_id')
    # --- Truncate all user-related tables ---
    op.execute('TRUNCATE TABLE answers, questions, group_members, group_creators, matches, match_statuses, users RESTART IDENTITY CASCADE;')

def downgrade():
    # --- Add columns back as nullable ---
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('telegram_user_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('telegram_id', sa.BigInteger(), nullable=True))
