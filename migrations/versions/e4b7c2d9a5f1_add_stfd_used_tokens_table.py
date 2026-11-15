"""add stfd used tokens table

Revision ID: e4b7c2d9a5f1
Revises: c8e2f4a6b1d3
Create Date: 2026-11-15 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4b7c2d9a5f1"
down_revision: Union[str, Sequence[str], None] = "c8e2f4a6b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "stfd_used_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stfd_used_tokens")),
        sa.UniqueConstraint("jti", name=op.f("uq_stfd_used_tokens_jti")),
    )
    op.create_index(op.f("ix_stfd_used_tokens_expires_at"), "stfd_used_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_stfd_used_tokens_expires_at"), table_name="stfd_used_tokens")
    op.drop_table("stfd_used_tokens")
