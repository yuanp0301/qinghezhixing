from datetime import datetime

from sqlalchemy import Integer, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ViewLog(Base):
    __tablename__ = "view_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(Integer)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
