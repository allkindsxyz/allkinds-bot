"""add status to answers

Revision ID: abcdef123456
Revises: f5c163a7142f
Create Date: 2025-05-23 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = 'f5c163a7142f'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('answers', sa.Column('status', sa.String(length=16), nullable=True))
    op.execute("UPDATE answers SET status = 'answered' WHERE value IS NOT NULL")
    op.execute("UPDATE answers SET status = 'delivered' WHERE value IS NULL")
    op.alter_column('answers', 'status', nullable=False, server_default='delivered')
    op.create_index('ix_answers_user_id_question_id_status', 'answers', ['user_id', 'question_id', 'status'])

def downgrade():
    op.drop_index('ix_answers_user_id_question_id_status', table_name='answers')
    op.drop_column('answers', 'status') 