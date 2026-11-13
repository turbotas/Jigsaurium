"""Tests for scripts/regenerate_image_derivatives.py (legacy images stored without real derivatives)."""

import importlib.util
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.db import get_session
from app.models import AuditEvent, JigsawImage

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "regenerate_image_derivatives.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("regenerate_image_derivatives", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _jpeg_with_gps(width=800, height=600):
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (51.0, 30.0, 0.0), 3: "W", 4: (0.0, 7.0, 0.0)}
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(90, 60, 30)).save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _add_legacy_image(db_session, image_data, *, sha):
    # Shape of rows written while Pillow was unavailable: derivatives are the original bytes.
    image = JigsawImage(
        jigsaw_id=None,
        tag="Box",
        filename="legacy.jpg",
        mime_type="image/jpeg",
        image_data=image_data,
        thumbnail_mime_type="image/jpeg",
        thumbnail_data=image_data,
        preview_mime_type="image/jpeg",
        preview_data=image_data,
        image_sha256=sha,
        content_version=1,
    )
    db_session.add(image)
    db_session.commit()
    return image.id


@pytest.mark.functional
def test_regenerates_legacy_derivatives_and_strips_exif(app):
    script = _load_script()
    original = _jpeg_with_gps()
    with app.app_context():
        db_session = get_session()
        image_id = _add_legacy_image(db_session, original, sha="a" * 64)

        assert script.find_affected_image_ids(db_session) == [image_id]
        summary = script.regenerate_image_derivatives(db_session, [image_id])

        assert summary["regenerated"] == 1
        image = db_session.get(JigsawImage, image_id)
        assert image.content_version == 2
        assert image.thumbnail_data != original
        with Image.open(BytesIO(image.thumbnail_data)) as thumbnail:
            assert thumbnail.width == 150
            assert not thumbnail.getexif().get_ifd(0x8825)
        with Image.open(BytesIO(image.preview_data)) as preview:
            assert preview.width == 600

        assert script.find_affected_image_ids(db_session) == []
        audit = db_session.query(AuditEvent).filter_by(action=script.AUDIT_ACTION).one()
        assert json.loads(audit.payload_json)["regenerated"] == 1


@pytest.mark.functional
def test_dry_run_reports_without_writing(app):
    script = _load_script()
    original = _jpeg_with_gps()
    with app.app_context():
        db_session = get_session()
        image_id = _add_legacy_image(db_session, original, sha="b" * 64)

        summary = script.regenerate_image_derivatives(db_session, [image_id], dry_run=True)

        assert summary["regenerated"] == 1
        image = db_session.get(JigsawImage, image_id)
        assert image.thumbnail_data == original
        assert image.content_version == 1
        assert db_session.query(AuditEvent).filter_by(action=script.AUDIT_ACTION).count() == 0


@pytest.mark.functional
def test_undecodable_image_gets_empty_derivatives(app):
    script = _load_script()
    junk = b"not-an-image" * 10
    with app.app_context():
        db_session = get_session()
        image_id = _add_legacy_image(db_session, junk, sha="c" * 64)

        summary = script.regenerate_image_derivatives(db_session, [image_id])

        assert summary["undecodable"] == [image_id]
        image = db_session.get(JigsawImage, image_id)
        assert image.thumbnail_data is None
        assert image.preview_data is None
