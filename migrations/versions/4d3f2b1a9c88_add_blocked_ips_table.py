"""add blocked ips table

Revision ID: 4d3f2b1a9c88
Revises: 7a1c2e8d4f99
Create Date: 2026-10-19 20:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d3f2b1a9c88"
down_revision: Union[str, Sequence[str], None] = "7a1c2e8d4f99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blocked_ips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("block_source", sa.String(length=32), nullable=False),
        sa.Column("block_reason", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_blocked_ips_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blocked_ips")),
    )
    with op.batch_alter_table("blocked_ips") as batch_op:
        batch_op.create_index(op.f("ix_blocked_ips_blocked_until"), ["blocked_until"], unique=False)
        batch_op.create_index(op.f("ix_blocked_ips_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_index(op.f("ix_blocked_ips_ip_address"), ["ip_address"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("blocked_ips") as batch_op:
        batch_op.drop_index(op.f("ix_blocked_ips_ip_address"))
        batch_op.drop_index(op.f("ix_blocked_ips_created_by_user_id"))
        batch_op.drop_index(op.f("ix_blocked_ips_blocked_until"))

    op.drop_table("blocked_ips")
