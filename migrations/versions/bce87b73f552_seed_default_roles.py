"""seed default roles

Revision ID: bce87b73f552
Revises: c67b672955db
Create Date: 2026-06-22 11:39:50.705882

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bce87b73f552'
down_revision: Union[str, Sequence[str], None] = 'c67b672955db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    roles_table = sa.table(
        "roles",
        sa.column("name", sa.String(length=64)),
        sa.column("description", sa.String(length=255)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    created_at = datetime.now(timezone.utc)
    op.bulk_insert(
        roles_table,
        [
            {
                "name": "administrator",
                "description": "Full administrative access",
                "created_at": created_at,
            },
            {
                "name": "borrower",
                "description": "Borrower catalog and loan access",
                "created_at": created_at,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM roles WHERE name IN ('administrator', 'borrower')"))
