"""normalize image browser tags to camel case

Revision ID: 3e6c1d2a9f44
Revises: 5f2d1a8b3c44
Create Date: 2026-10-13 17:20:00.000000

"""

from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3e6c1d2a9f44"
down_revision: Union[str, Sequence[str], None] = "5f2d1a8b3c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_known_image_tag(value):
    normalized = str(value or "").strip()
    if not normalized:
        return normalized

    collapsed = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    canonical_tags = {
        "box": "Box",
        "boxfront": "BoxFront",
        "boxside": "BoxSide",
        "boxback": "BoxBack",
        "completed": "Completed",
        "inprogress": "InProgress",
    }
    return canonical_tags.get(collapsed, normalized)


def _to_legacy_tag(value):
    if value == "BoxFront":
        return "box front"
    if value == "BoxSide":
        return "box-side"
    if value == "BoxBack":
        return "box-back"
    if value == "InProgress":
        return "in-progress"
    return value


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
    _retag_rows(_to_legacy_tag)
