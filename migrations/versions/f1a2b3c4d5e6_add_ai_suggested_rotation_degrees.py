"""add ai suggested rotation degrees to jigsaw images

Revision ID: f1a2b3c4d5e6
Revises: e2b1c4d5f678
Create Date: 2026-11-08 13:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e2b1c4d5f678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("ai_suggested_rotation_degrees", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jigsaw_images", "ai_suggested_rotation_degrees")
