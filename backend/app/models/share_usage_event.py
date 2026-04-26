from datetime import datetime

from sqlalchemy import Integer, Boolean, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShareUsageEvent(Base):
    __tablename__ = "share_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[int | None] = mapped_column(Integer)
    share_key_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("share_keys.id"))
    user_info: Mapped[str | None] = mapped_column(String(64))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    opened_via: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'download'"))
    is_offline_replay: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint("opened_via IN ('download')", name="ck_share_usage_events_opened_via"),
    )
