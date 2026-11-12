import hashlib
from io import BytesIO

from PIL import Image


def png_bytes(seed=b""):
    """Return a small, valid PNG whose pixels are derived from `seed`.

    Uploads are verified as real raster images, so tests that need distinct uploads (the
    library de-duplicates by content hash) pass a different seed for each image.
    """
    digest = hashlib.sha256(bytes(seed)).digest()
    image = Image.new("RGB", (4, 4))
    image.putdata([tuple(digest[index * 3 : index * 3 + 3]) for index in range(10)] + [(0, 0, 0)] * 6)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes(seed=b""):
    """Return a small, valid JPEG whose colour is derived from `seed`."""
    digest = hashlib.sha256(bytes(seed)).digest()
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=tuple(digest[:3])).save(buffer, format="JPEG")
    return buffer.getvalue()
