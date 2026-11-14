"""replace ai suggested raw rotation with a separate skew angle

The AI now reports image rotation as two parts: a quarter-turn orientation
(kept in ai_suggested_rotation_degrees) and a small skew between -45 and 45
degrees. The old raw column held the full angle, so existing values are
converted to skew = raw - quarter turn.

Revision ID: c8e2f4a6b1d3
Revises: ab12cd34ef56
Create Date: 2026-11-13 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e2f4a6b1d3"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _skew_from_raw(raw, quarter_turn):
    skew = (float(raw) - float(quarter_turn or 0)) % 360.0
    if skew > 180.0:
        skew -= 360.0
    return round(max(-45.0, min(45.0, skew)), 6)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("ai_suggested_skew_degrees", sa.Float(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, ai_suggested_rotation_degrees, ai_suggested_rotation_degrees_raw "
            "FROM jigsaw_images WHERE ai_suggested_rotation_degrees_raw IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE jigsaw_images SET ai_suggested_skew_degrees = :skew WHERE id = :id"),
            {"skew": _skew_from_raw(row[2], row[1]), "id": row[0]},
        )

    op.drop_column("jigsaw_images", "ai_suggested_rotation_degrees_raw")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("jigsaw_images", sa.Column("ai_suggested_rotation_degrees_raw", sa.Float(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, ai_suggested_rotation_degrees, ai_suggested_skew_degrees "
            "FROM jigsaw_images WHERE ai_suggested_skew_degrees IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        raw = (float(row[1] or 0) + float(row[2])) % 360.0
        connection.execute(
            sa.text("UPDATE jigsaw_images SET ai_suggested_rotation_degrees_raw = :raw WHERE id = :id"),
            {"raw": round(raw, 6), "id": row[0]},
        )

    op.drop_column("jigsaw_images", "ai_suggested_skew_degrees")
