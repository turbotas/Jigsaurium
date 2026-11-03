from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class DatabaseBackup(Base):
    __tablename__ = "database_backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    initiated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    file_format: Mapped[str] = mapped_column(String(32), nullable=False, default="mysql_sql")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    app_environment: Mapped[str] = mapped_column(String(32), nullable=False)
    app_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
