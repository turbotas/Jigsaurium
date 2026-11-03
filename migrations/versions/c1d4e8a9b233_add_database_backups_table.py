"""add database backups table

Revision ID: c1d4e8a9b233
Revises: a8b3d9c1e244
Create Date: 2026-11-03 14:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d4e8a9b233"
down_revision: Union[str, Sequence[str], None] = "a8b3d9c1e244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "database_backups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_format", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("app_environment", sa.String(length=32), nullable=False),
        sa.Column("app_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["initiated_by_user_id"],
            ["users.id"],
            name=op.f("fk_database_backups_initiated_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_database_backups")),
        sa.UniqueConstraint("filename", name=op.f("uq_database_backups_filename")),
        sa.UniqueConstraint("storage_path", name=op.f("uq_database_backups_storage_path")),
    )
    op.create_index(op.f("ix_database_backups_created_at"), "database_backups", ["created_at"], unique=False)
    op.create_index(op.f("ix_database_backups_initiated_by_user_id"), "database_backups", ["initiated_by_user_id"], unique=False)
    op.create_index(op.f("ix_database_backups_status"), "database_backups", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_database_backups_status"), table_name="database_backups")
    op.drop_index(op.f("ix_database_backups_initiated_by_user_id"), table_name="database_backups")
    op.drop_index(op.f("ix_database_backups_created_at"), table_name="database_backups")
    op.drop_table("database_backups")
