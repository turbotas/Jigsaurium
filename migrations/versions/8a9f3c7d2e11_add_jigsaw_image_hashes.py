"""add jigsaw image hashes

Revision ID: 8a9f3c7d2e11
Revises: 7d2c8a1f5b44
Create Date: 2026-10-14 09:20:00.000000

"""
from hashlib import sha256
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a9f3c7d2e11"
down_revision: Union[str, Sequence[str], None] = "7d2c8a1f5b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("image_sha256", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, image_data FROM jigsaw_images")).fetchall()
    for row in rows:
        image_id = row[0]
        image_data = row[1] or b""
        digest = sha256(image_data).hexdigest()
        connection.execute(
            sa.text("UPDATE jigsaw_images SET image_sha256 = :digest WHERE id = :image_id"),
            {"digest": digest, "image_id": image_id},
        )

    op.create_index(op.f("ix_jigsaw_images_image_sha256"), "jigsaw_images", ["image_sha256"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_jigsaw_images_image_sha256"), table_name="jigsaw_images")
    op.drop_column("jigsaw_images", "image_sha256")
