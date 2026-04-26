from datetime import datetime

from sqlalchemy import Integer, CheckConstraint, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShareAccessLog(Base):
    __tablename__ = "share_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[int | None] = mapped_column(Integer)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        CheckConstraint("result IN ('success','expired','revoked','not_found')", name="ck_share_access_logs_result"),
    )
