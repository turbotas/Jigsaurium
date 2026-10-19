"""add user comment to jigsaw images

Revision ID: 6b9d3e1f4a22
Revises: e2a4c6f8b9d1
Create Date: 2026-10-17 18:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b9d3e1f4a22"
down_revision: Union[str, Sequence[str], None] = "e2a4c6f8b9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("user_comment", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jigsaw_images", "user_comment")
