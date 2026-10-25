"""add embedding compute duration ms

Revision ID: c3d9f1a6b244
Revises: b5f7c1d2e4a9
Create Date: 2026-10-25 12:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d9f1a6b244"
down_revision: Union[str, Sequence[str], None] = "b5f7c1d2e4a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("image_embeddings") as batch_op:
        batch_op.add_column(sa.Column("compute_duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("image_embeddings") as batch_op:
        batch_op.drop_column("compute_duration_ms")
