"""add jigsaw diary entries

Revision ID: 4b8e2a1c9d05
Revises: 2d3a9be41f7c
Create Date: 2026-10-13 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b8e2a1c9d05"
down_revision: Union[str, Sequence[str], None] = "2d3a9be41f7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "jigsaw_diary_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jigsaw_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["jigsaw_id"], ["jigsaws.id"], name=op.f("fk_jigsaw_diary_entries_jigsaw_id_jigsaws"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jigsaw_diary_entries")),
    )
    op.create_index(op.f("ix_jigsaw_diary_entries_jigsaw_id"), "jigsaw_diary_entries", ["jigsaw_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_jigsaw_diary_entries_jigsaw_id"), table_name="jigsaw_diary_entries")
    op.drop_table("jigsaw_diary_entries")
