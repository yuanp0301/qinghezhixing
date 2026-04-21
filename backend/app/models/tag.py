from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    contents: Mapped[list["Content"]] = relationship(  # noqa: F821
        secondary="content_tags",
        back_populates="tags",
    )


class ContentTag(Base):
    __tablename__ = "content_tags"

    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("contents.id", ondelete="CASCADE"),
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
    )

    __table_args__ = (
        PrimaryKeyConstraint("content_id", "tag_id"),
        Index("ix_content_tags_tag", "tag_id"),
    )
