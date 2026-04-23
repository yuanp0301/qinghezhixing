"""add share_usage_events table

Revision ID: 4b78dbf8a9e2
Revises: 9e20ebd2ac11
Create Date: 2026-04-23 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4b78dbf8a9e2"
down_revision: Union[str, Sequence[str], None] = "9e20ebd2ac11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "share_usage_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("content_id", sa.BigInteger(), nullable=True),
        sa.Column("share_key_id", sa.BigInteger(), nullable=True),
        sa.Column("user_info", sa.String(length=64), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("opened_via", sa.String(length=16), server_default=sa.text("'download'"), nullable=False),
        sa.Column("is_offline_replay", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("client_ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.CheckConstraint("opened_via IN ('download')", name="ck_share_usage_events_opened_via"),
        sa.ForeignKeyConstraint(["share_key_id"], ["share_keys.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_share_usage_events_token_reported_at",
        "share_usage_events",
        ["token", "reported_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_share_usage_events_token_reported_at", table_name="share_usage_events")
    op.drop_table("share_usage_events")
