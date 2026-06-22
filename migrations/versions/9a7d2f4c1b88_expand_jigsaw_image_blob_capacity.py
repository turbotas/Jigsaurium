"""expand jigsaw image blob capacity

Revision ID: 9a7d2f4c1b88
Revises: f3a1c5d9b2e7
Create Date: 2026-06-22 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9a7d2f4c1b88"
down_revision: Union[str, Sequence[str], None] = "f3a1c5d9b2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name in {"mysql", "mariadb"}:
        op.execute("ALTER TABLE jigsaw_images MODIFY image_data LONGBLOB NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name in {"mysql", "mariadb"}:
        op.execute("ALTER TABLE jigsaw_images MODIFY image_data BLOB NOT NULL")
