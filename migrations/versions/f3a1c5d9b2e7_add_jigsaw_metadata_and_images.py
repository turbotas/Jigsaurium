"""add jigsaw metadata and images

Revision ID: f3a1c5d9b2e7
Revises: 8f2cb5dca8d1
Create Date: 2026-06-22 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a1c5d9b2e7"
down_revision: Union[str, Sequence[str], None] = "8f2cb5dca8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaws", sa.Column("manufacturer", sa.String(length=255), nullable=True))
    op.add_column("jigsaws", sa.Column("artist", sa.String(length=255), nullable=True))
    op.add_column("jigsaws", sa.Column("dimensions_cm", sa.String(length=64), nullable=True))
    op.add_column("jigsaws", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("jigsaws", sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "jigsaw_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jigsaw_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["jigsaw_id"], ["jigsaws.id"], name=op.f("fk_jigsaw_images_jigsaw_id_jigsaws"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jigsaw_images")),
    )
    op.create_index(op.f("ix_jigsaw_images_jigsaw_id"), "jigsaw_images", ["jigsaw_id"], unique=False)
    op.create_index(op.f("ix_jigsaw_images_tag"), "jigsaw_images", ["tag"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_jigsaw_images_tag"), table_name="jigsaw_images")
    op.drop_index(op.f("ix_jigsaw_images_jigsaw_id"), table_name="jigsaw_images")
    op.drop_table("jigsaw_images")

    op.drop_column("jigsaws", "last_completed_at")
    op.drop_column("jigsaws", "description")
    op.drop_column("jigsaws", "dimensions_cm")
    op.drop_column("jigsaws", "artist")
    op.drop_column("jigsaws", "manufacturer")
