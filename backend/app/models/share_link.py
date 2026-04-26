from datetime import datetime

from sqlalchemy import (
    Integer, Boolean, DateTime, ForeignKey, Index, String, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("contents.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allow_download: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        Index("ix_share_links_content_created", "content_id", "created_at"),
        Index("ix_share_links_created_by_created", "created_by", "created_at"),
    )
