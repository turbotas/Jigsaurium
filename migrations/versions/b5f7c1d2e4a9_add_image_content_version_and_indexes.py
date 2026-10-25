"""add image content version and indexes

Revision ID: b5f7c1d2e4a9
Revises: 2c4e8a9d1b33
Create Date: 2026-10-25 11:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5f7c1d2e4a9"
down_revision: Union[str, Sequence[str], None] = "2c4e8a9d1b33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.add_column(sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_index(op.f("ix_jigsaw_images_jigsaw_id_id"), ["jigsaw_id", "id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.drop_index(op.f("ix_jigsaw_images_jigsaw_id_id"))
        batch_op.drop_column("content_version")
