"""add stored thumbnail and preview variants for jigsaw images

Revision ID: a4f9d2b7c3e1
Revises: 9c4d8e1a2b77
Create Date: 2026-10-14 13:35:00.000000

"""

from io import BytesIO
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

try:  # pragma: no cover - optional dependency fallback
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        pass


# revision identifiers, used by Alembic.
revision: str = "a4f9d2b7c3e1"
down_revision: Union[str, Sequence[str], None] = "9c4d8e1a2b77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

THUMBNAIL_TARGET_WIDTH = 150
PREVIEW_TARGET_WIDTH = 600


def _resize_image_for_width(image, target_width):
    if target_width <= 0:
        return image.copy()

    width = max(1, int(image.width))
    height = max(1, int(image.height))
    if width <= target_width:
        return image.copy()

    ratio = target_width / float(width)
    next_size = (target_width, max(1, int(round(height * ratio))))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    return image.resize(next_size, resampling)


def _encode_variant_image(image):
    has_alpha = "A" in image.getbands() or image.mode in {"LA", "RGBA", "PA"}
    output_buffer = BytesIO()
    if has_alpha:
        encoded = image.convert("RGBA")
        encoded.save(output_buffer, format="PNG", optimize=True)
        return "image/png", output_buffer.getvalue()

    encoded = image.convert("RGB")
    encoded.save(output_buffer, format="JPEG", quality=82, optimize=True, progressive=True)
    return "image/jpeg", output_buffer.getvalue()


def _build_variants(image_data, mime_type):
    fallback = {
        "thumbnail_mime_type": mime_type,
        "thumbnail_data": image_data,
        "preview_mime_type": mime_type,
        "preview_data": image_data,
    }
    if Image is None or ImageOps is None:
        return fallback

    try:
        with Image.open(BytesIO(image_data)) as source_image:
            normalized = ImageOps.exif_transpose(source_image)
            thumbnail_image = _resize_image_for_width(normalized, THUMBNAIL_TARGET_WIDTH)
            preview_image = _resize_image_for_width(normalized, PREVIEW_TARGET_WIDTH)
            thumbnail_mime_type, thumbnail_data = _encode_variant_image(thumbnail_image)
            preview_mime_type, preview_data = _encode_variant_image(preview_image)
    except (UnidentifiedImageError, OSError, ValueError):
        return fallback

    return {
        "thumbnail_mime_type": thumbnail_mime_type,
        "thumbnail_data": thumbnail_data,
        "preview_mime_type": preview_mime_type,
        "preview_data": preview_data,
    }


def _backfill_variants() -> None:
    bind = op.get_bind()
    images_table = sa.table(
        "jigsaw_images",
        sa.column("id", sa.Integer()),
        sa.column("mime_type", sa.String(length=128)),
        sa.column("image_data", sa.LargeBinary()),
        sa.column("thumbnail_mime_type", sa.String(length=128)),
        sa.column("thumbnail_data", sa.LargeBinary()),
        sa.column("preview_mime_type", sa.String(length=128)),
        sa.column("preview_data", sa.LargeBinary()),
    )

    rows = bind.execute(sa.select(images_table.c.id, images_table.c.mime_type, images_table.c.image_data)).mappings()
    for row in rows:
        image_data = row.get("image_data")
        mime_type = row.get("mime_type")
        if not image_data or not mime_type:
            continue

        variants = _build_variants(image_data, mime_type)
        bind.execute(
            sa.update(images_table)
            .where(images_table.c.id == row["id"])
            .values(
                thumbnail_mime_type=variants["thumbnail_mime_type"],
                thumbnail_data=variants["thumbnail_data"],
                preview_mime_type=variants["preview_mime_type"],
                preview_data=variants["preview_data"],
            )
        )


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jigsaw_images", sa.Column("thumbnail_mime_type", sa.String(length=128), nullable=True))
    op.add_column(
        "jigsaw_images",
        sa.Column("thumbnail_data", sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=True),
    )
    op.add_column("jigsaw_images", sa.Column("preview_mime_type", sa.String(length=128), nullable=True))
    op.add_column(
        "jigsaw_images",
        sa.Column("preview_data", sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"), nullable=True),
    )

    _backfill_variants()


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jigsaw_images", "preview_data")
    op.drop_column("jigsaw_images", "preview_mime_type")
    op.drop_column("jigsaw_images", "thumbnail_data")
    op.drop_column("jigsaw_images", "thumbnail_mime_type")
