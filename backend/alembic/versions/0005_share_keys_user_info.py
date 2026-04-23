"""add user_info to share_keys

Revision ID: 9e20ebd2ac11
Revises: 7a4c42d27d01
Create Date: 2026-04-22 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e20ebd2ac11"
down_revision: Union[str, Sequence[str], None] = "7a4c42d27d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "share_keys",
        sa.Column("user_info", sa.String(length=64), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("share_keys", "user_info")
