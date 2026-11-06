"""add login throttle counters table

Revision ID: d9a7c4e2b611
Revises: c1d4e8a9b233
Create Date: 2026-11-06 16:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9a7c4e2b611"
down_revision: Union[str, Sequence[str], None] = "c1d4e8a9b233"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "login_throttle_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_throttle_counters")),
        sa.UniqueConstraint("client_ip", "email", name=op.f("uq_login_throttle_counters_client_ip_email")),
    )
    op.create_index(
        op.f("ix_login_throttle_counters_client_ip"),
        "login_throttle_counters",
        ["client_ip"],
        unique=False,
    )
    op.create_index(
        op.f("ix_login_throttle_counters_blocked_until"),
        "login_throttle_counters",
        ["blocked_until"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_login_throttle_counters_blocked_until"), table_name="login_throttle_counters")
    op.drop_index(op.f("ix_login_throttle_counters_client_ip"), table_name="login_throttle_counters")
    op.drop_table("login_throttle_counters")
