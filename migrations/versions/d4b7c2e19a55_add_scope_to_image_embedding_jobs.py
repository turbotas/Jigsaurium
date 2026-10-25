"""add scope to image embedding jobs

Revision ID: d4b7c2e19a55
Revises: c3d9f1a6b244
Create Date: 2026-10-25 13:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4b7c2e19a55"
down_revision: Union[str, Sequence[str], None] = "c3d9f1a6b244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("image_embedding_jobs") as batch_op:
        batch_op.add_column(sa.Column("scope", sa.String(length=16), nullable=False, server_default="all"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("image_embedding_jobs") as batch_op:
        batch_op.drop_column("scope")
