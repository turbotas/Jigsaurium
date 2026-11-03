"""add user sessions table

Revision ID: a8b3d9c1e244
Revises: d4b7c2e19a55
Create Date: 2026-11-03 11:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b3d9c1e244"
down_revision: Union[str, Sequence[str], None] = "d4b7c2e19a55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_identifier", sa.String(length=128), nullable=False),
        sa.Column("origin_ip_address", sa.String(length=64), nullable=True),
        sa.Column("auth_provider", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("termination_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["terminated_by_user_id"], ["users.id"], name=op.f("fk_user_sessions_terminated_by_user_id_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_sessions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("session_identifier", name=op.f("uq_user_sessions_session_identifier")),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_sessions_last_activity_at"), "user_sessions", ["last_activity_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_sessions_last_activity_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
