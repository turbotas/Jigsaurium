"""add jigsaw series fields

Revision ID: 1b7e4a6c9d21
Revises: 8a9f3c7d2e11
Create Date: 2026-10-14 09:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b7e4a6c9d21"
down_revision: Union[str, Sequence[str], None] = "8a9f3c7d2e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaws", sa.Column("series_name", sa.String(length=255), nullable=True))
    op.add_column("jigsaws", sa.Column("series_number", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jigsaws", "series_number")
    op.drop_column("jigsaws", "series_name")
