from datetime import datetime

from sqlalchemy import (
    Integer,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploader_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    oss_bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    oss_object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'public_in_site'"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="content_tags",
        back_populates="contents",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public_in_site','private')",
            name="ck_contents_visibility",
        ),
        CheckConstraint(
            "status IN ('active','deleted')", name="ck_contents_status"
        ),
        Index("ix_contents_uploader_created", "uploader_id", "created_at"),
        Index("ix_contents_visibility_created", "visibility", "created_at"),
        Index("ix_contents_sha256", "sha256"),
    )
