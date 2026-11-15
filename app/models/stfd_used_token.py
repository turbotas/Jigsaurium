from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class StfdUsedToken(Base):
    """An STFD sign-in token id (`jti`) that has already been used, kept until the token could no longer pass anyway.

    The unique `jti` column is the replay check: a second insert of the same id fails.
    """

    __tablename__ = "stfd_used_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
