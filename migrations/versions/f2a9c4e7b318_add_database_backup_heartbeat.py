"""add heartbeat_at to database backups

Revision ID: f2a9c4e7b318
Revises: e4b7c2d9a5f1
Create Date: 2026-11-23 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a9c4e7b318"
down_revision: Union[str, Sequence[str], None] = "e4b7c2d9a5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("database_backups") as batch_op:
        batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("database_backups") as batch_op:
        batch_op.drop_column("heartbeat_at")
