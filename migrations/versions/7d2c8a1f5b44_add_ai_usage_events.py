"""add ai usage events

Revision ID: 7d2c8a1f5b44
Revises: 6c1f0e2d9a11
Create Date: 2026-10-13 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d2c8a1f5b44"
down_revision: Union[str, Sequence[str], None] = "6c1f0e2d9a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("endpoint_url", sa.String(length=512), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("computed_cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("final_cost_usd", sa.Numeric(precision=12, scale=6), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_ai_usage_events_actor_user_id_users")),
        sa.ForeignKeyConstraint(
            ["image_id"],
            ["jigsaw_images.id"],
            name=op.f("fk_ai_usage_events_image_id_jigsaw_images"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_usage_events")),
    )
    op.create_index(op.f("ix_ai_usage_events_created_at"), "ai_usage_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_ai_usage_events_operation"), "ai_usage_events", ["operation"], unique=False)
    op.create_index(op.f("ix_ai_usage_events_status"), "ai_usage_events", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ai_usage_events_status"), table_name="ai_usage_events")
    op.drop_index(op.f("ix_ai_usage_events_operation"), table_name="ai_usage_events")
    op.drop_index(op.f("ix_ai_usage_events_created_at"), table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
