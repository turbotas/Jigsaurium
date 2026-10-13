"""normalize image browser tags to title case labels

Revision ID: 9c4d8e1a2b77
Revises: 3e6c1d2a9f44
Create Date: 2026-10-13 18:05:00.000000

"""

from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4d8e1a2b77"
down_revision: Union[str, Sequence[str], None] = "3e6c1d2a9f44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_known_image_tag(value):
    normalized = str(value or "").strip()
    if not normalized:
        return normalized

    collapsed = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    canonical_tags = {
        "box": "Box",
        "boxfront": "Box front",
        "boxside": "Box side",
        "boxback": "Box back",
        "completed": "Completed",
        "inprogress": "In progress",
    }
    return canonical_tags.get(collapsed, normalized)


def _retag_rows(transform):
    bind = op.get_bind()
    images_table = sa.table(
        "jigsaw_images",
        sa.column("id", sa.Integer()),
        sa.column("tag", sa.String(length=64)),
    )

    rows = bind.execute(sa.select(images_table.c.id, images_table.c.tag)).all()
    for image_id, tag in rows:
        next_tag = transform(tag)
        if next_tag == tag:
            continue

        bind.execute(
            sa.update(images_table)
            .where(images_table.c.id == image_id)
            .values(tag=next_tag)
        )


def upgrade() -> None:
    """Upgrade schema."""
    _retag_rows(_normalize_known_image_tag)


def downgrade() -> None:
    """Downgrade schema."""

    def _to_camel_case(value):
        normalized = str(value or "").strip()
        mapping = {
            "Box front": "BoxFront",
            "Box side": "BoxSide",
            "Box back": "BoxBack",
            "In progress": "InProgress",
        }
        return mapping.get(normalized, normalized)

    _retag_rows(_to_camel_case)
