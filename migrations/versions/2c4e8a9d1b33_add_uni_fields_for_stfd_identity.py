"""add uni fields for stfd identity

Revision ID: 2c4e8a9d1b33
Revises: 7a1c2e8d4f99
Create Date: 2026-10-21 14:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c4e8a9d1b33"
down_revision: Union[str, Sequence[str], None] = "4d3f2b1a9c88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("roles", sa.Column("uni", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_roles_uni"), "roles", ["uni"], unique=True)
    op.create_index(op.f("ix_users_auth_subject"), "users", ["auth_subject"], unique=False)
    op.create_index(op.f("ix_users_auth_subject_unique"), "users", ["auth_subject"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_auth_subject_unique"), table_name="users")
    op.drop_index(op.f("ix_users_auth_subject"), table_name="users")
    op.drop_index(op.f("ix_roles_uni"), table_name="roles")
    op.drop_column("roles", "uni")
