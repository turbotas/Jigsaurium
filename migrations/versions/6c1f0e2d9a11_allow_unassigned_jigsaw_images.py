"""allow unassigned jigsaw images

Revision ID: 6c1f0e2d9a11
Revises: 4b8e2a1c9d05
Create Date: 2026-10-13 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c1f0e2d9a11"
down_revision: Union[str, Sequence[str], None] = "4b8e2a1c9d05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.alter_column("jigsaw_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM jigsaw_images WHERE jigsaw_id IS NULL")
    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.alter_column("jigsaw_id", existing_type=sa.Integer(), nullable=False)
