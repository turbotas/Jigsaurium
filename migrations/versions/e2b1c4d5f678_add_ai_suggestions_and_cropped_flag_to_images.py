"""add ai suggestion fields and cropped flag to jigsaw images

Revision ID: e2b1c4d5f678
Revises: d9a7c4e2b611
Create Date: 2026-11-08 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2b1c4d5f678"
down_revision: Union[str, Sequence[str], None] = "d9a7c4e2b611"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "jigsaw_images",
        sa.Column("is_cropped", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("jigsaw_images", sa.Column("ai_suggested_tag", sa.String(length=64), nullable=True))
    op.add_column("jigsaw_images", sa.Column("ai_suggested_corners_json", sa.String(length=2000), nullable=True))
    op.add_column(
        "jigsaw_images",
        sa.Column("ai_suggestions_pending_review", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("jigsaw_images", sa.Column("ai_suggested_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jigsaw_images", "ai_suggested_at")
    op.drop_column("jigsaw_images", "ai_suggestions_pending_review")
    op.drop_column("jigsaw_images", "ai_suggested_corners_json")
    op.drop_column("jigsaw_images", "ai_suggested_tag")
    op.drop_column("jigsaw_images", "is_cropped")
