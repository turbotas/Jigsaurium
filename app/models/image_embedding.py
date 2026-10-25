from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("jigsaw_images.id", ondelete="CASCADE"), nullable=False)
    model_key: Mapped[str] = mapped_column(String(255), nullable=False)
    vector_json: Mapped[str] = mapped_column(Text(), nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer(), nullable=False)
    source_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    compute_duration_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
