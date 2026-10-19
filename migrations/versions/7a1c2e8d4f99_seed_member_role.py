"""seed member role

Revision ID: 7a1c2e8d4f99
Revises: f4c3b2a190de
Create Date: 2026-10-19 13:05:00.000000

"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1c2e8d4f99"
down_revision: Union[str, Sequence[str], None] = "f4c3b2a190de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    existing = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'member' LIMIT 1")).scalar_one_or_none()
    if existing is not None:
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO roles (name, description, created_at)
            VALUES (:name, :description, :created_at)
            """
        ),
        {
            "name": "member",
            "description": "Shared household member access",
            "created_at": datetime.now(timezone.utc),
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM roles WHERE name = 'member'"))
