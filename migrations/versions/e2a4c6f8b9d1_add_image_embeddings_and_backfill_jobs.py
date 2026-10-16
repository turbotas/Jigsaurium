"""add image embeddings and backfill jobs

Revision ID: e2a4c6f8b9d1
Revises: d1f4a3b2c9e8
Create Date: 2026-10-16 12:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2a4c6f8b9d1"
down_revision: Union[str, Sequence[str], None] = "d1f4a3b2c9e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "image_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False),
        sa.Column("vector_dim", sa.Integer(), nullable=False),
        sa.Column("source_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["image_id"], ["jigsaw_images.id"], name=op.f("fk_image_embeddings_image_id_jigsaw_images"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image_embeddings")),
        sa.UniqueConstraint("image_id", "model_key", name=op.f("uq_image_embeddings_image_id_model_key")),
    )
    op.create_index(op.f("ix_image_embeddings_model_key"), "image_embeddings", ["model_key"], unique=False)

    op.create_table(
        "image_embedding_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("succeeded_items", sa.Integer(), nullable=False),
        sa.Column("failed_items", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("error_summary_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_image_embedding_jobs_actor_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image_embedding_jobs")),
    )
    op.create_index(op.f("ix_image_embedding_jobs_status"), "image_embedding_jobs", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_image_embedding_jobs_status"), table_name="image_embedding_jobs")
    op.drop_table("image_embedding_jobs")

    op.drop_index(op.f("ix_image_embeddings_model_key"), table_name="image_embeddings")
    op.drop_table("image_embeddings")
