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
    jigsaw_id: Mapped[int | None] = mapped_column(ForeignKey("jigsaws.id", ondelete="CASCADE"), nullable=True)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=False)
    thumbnail_mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    thumbnail_data: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=True
    )
    preview_mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preview_data: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=True
    )
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    captured_at_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
