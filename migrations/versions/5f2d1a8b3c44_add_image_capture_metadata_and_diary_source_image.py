"""add image capture metadata and diary source image link

Revision ID: 5f2d1a8b3c44
Revises: 1b7e4a6c9d21
Create Date: 2026-10-14 10:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f2d1a8b3c44"
down_revision: Union[str, Sequence[str], None] = "1b7e4a6c9d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jigsaw_images", sa.Column("captured_at_source", sa.String(length=32), nullable=True))
    op.add_column("jigsaw_images", sa.Column("captured_at_raw", sa.String(length=64), nullable=True))

    with op.batch_alter_table("jigsaw_diary_entries") as batch_op:
        batch_op.add_column(sa.Column("source_image_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint(
            op.f("uq_jigsaw_diary_entries_source_image_id"),
            ["source_image_id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_jigsaw_diary_entries_source_image_id_jigsaw_images"),
            "jigsaw_images",
            ["source_image_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("jigsaw_diary_entries") as batch_op:
        batch_op.drop_constraint(op.f("fk_jigsaw_diary_entries_source_image_id_jigsaw_images"), type_="foreignkey")
        batch_op.drop_constraint(op.f("uq_jigsaw_diary_entries_source_image_id"), type_="unique")
        batch_op.drop_column("source_image_id")

    op.drop_column("jigsaw_images", "captured_at_raw")
    op.drop_column("jigsaw_images", "captured_at_source")
    op.drop_column("jigsaw_images", "captured_at")
