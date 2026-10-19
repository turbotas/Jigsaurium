from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BlockedIp(Base):
    __tablename__ = "blocked_ips"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    blocked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    block_source: Mapped[str] = mapped_column(String(32), nullable=False)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
