from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects import mysql

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class JigsawImage(Base):
    __tablename__ = "jigsaw_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    jigsaw_id: Mapped[int] = mapped_column(ForeignKey("jigsaws.id", ondelete="CASCADE"), nullable=False)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
