"""add admin to group_creators

Revision ID: 274a0e133760
Revises: 5c6bd04ee3ea
Create Date: 2025-05-27 15:44:04.569177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# TODO: Впиши сюда актуальный user_id админа (узнай через SELECT id FROM users; после входа админа в бота)
ADMIN_USER_ID = 1

# revision identifiers, used by Alembic.
revision: str = '274a0e133760'
down_revision: Union[str, None] = '5c6bd04ee3ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"INSERT INTO group_creators (user_id, created_at) VALUES ({ADMIN_USER_ID}, NOW())"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"DELETE FROM group_creators WHERE user_id = {ADMIN_USER_ID}"
    )
