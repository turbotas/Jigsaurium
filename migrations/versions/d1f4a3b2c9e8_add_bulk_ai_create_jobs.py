"""add bulk ai create job tracking tables

Revision ID: d1f4a3b2c9e8
Revises: a4f9d2b7c3e1
Create Date: 2026-10-15 15:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1f4a3b2c9e8"
down_revision: Union[str, Sequence[str], None] = "a4f9d2b7c3e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bulk_ai_create_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("succeeded_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("error_summary_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_bulk_ai_create_jobs_actor_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bulk_ai_create_jobs")),
    )
    op.create_index(op.f("ix_bulk_ai_create_jobs_created_at"), "bulk_ai_create_jobs", ["created_at"], unique=False)
    op.create_index(op.f("ix_bulk_ai_create_jobs_status"), "bulk_ai_create_jobs", ["status"], unique=False)

    op.create_table(
        "bulk_ai_create_job_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("jigsaw_id", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["image_id"], ["jigsaw_images.id"], name=op.f("fk_bulk_ai_create_job_items_image_id_jigsaw_images"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["bulk_ai_create_jobs.id"], name=op.f("fk_bulk_ai_create_job_items_job_id_bulk_ai_create_jobs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jigsaw_id"], ["jigsaws.id"], name=op.f("fk_bulk_ai_create_job_items_jigsaw_id_jigsaws"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bulk_ai_create_job_items")),
    )
    op.create_index(op.f("ix_bulk_ai_create_job_items_job_id"), "bulk_ai_create_job_items", ["job_id"], unique=False)
    op.create_index(op.f("ix_bulk_ai_create_job_items_status"), "bulk_ai_create_job_items", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_bulk_ai_create_job_items_status"), table_name="bulk_ai_create_job_items")
    op.drop_index(op.f("ix_bulk_ai_create_job_items_job_id"), table_name="bulk_ai_create_job_items")
    op.drop_table("bulk_ai_create_job_items")

    op.drop_index(op.f("ix_bulk_ai_create_jobs_status"), table_name="bulk_ai_create_jobs")
    op.drop_index(op.f("ix_bulk_ai_create_jobs_created_at"), table_name="bulk_ai_create_jobs")
    op.drop_table("bulk_ai_create_jobs")
