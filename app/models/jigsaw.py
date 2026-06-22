import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class JigsawStatus(str, enum.Enum):
    AVAILABLE = "available"
    ON_LOAN = "on_loan"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class Jigsaw(Base):
    __tablename__ = "jigsaws"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dimensions_cm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    piece_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[JigsawStatus] = mapped_column(
        Enum(JigsawStatus, native_enum=False, length=32),
        nullable=False,
        default=JigsawStatus.AVAILABLE,
    )
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
