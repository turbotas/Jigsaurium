"""Regenerate thumbnail/preview derivatives for images stored without real ones.

Until the Pillow 13 import fix (v0.2.11), Pillow was silently unavailable in the API routes, so
every upload stored the original image bytes as its "thumbnail" and "preview". Guests are served
those variants, so they received original photos, including EXIF location data.

This script finds images whose thumbnail or preview is missing or byte-identical to the original,
re-encodes the derivatives, and bumps content_version when they change so browsers stop using
cached copies. It is safe to re-run; images that already have real derivatives are skipped.

Run inside the app container (uses the container's DATABASE_URL):
    docker exec <container> python scripts/regenerate_image_derivatives.py --dry-run
    docker exec <container> python scripts/regenerate_image_derivatives.py

Or, for an environment run from the repo with run.bat / run.sh (reads the repo's .env):
    .venv\\Scripts\\python.exe scripts\\regenerate_image_derivatives.py --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - containers pass settings as real env vars
    load_dotenv = None

# Read the repo's .env like run.py does, so a local run (run.bat) finds the same database.
# Real environment variables (the container's) take precedence.
if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")

# The embedding model is not needed here; skip the slow warm-load during app creation.
# Overrides any env setting (the image sets it to 1) so the script starts quickly.
os.environ["IMAGE_EMBEDDINGS_WARM_ON_STARTUP"] = "0"

from sqlalchemy import or_, select  # noqa: E402

from app import create_app  # noqa: E402
from app.api.v1 import routes as api_routes  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import AuditEvent, JigsawImage  # noqa: E402

AUDIT_ACTION = "system.image_derivatives_regenerated"


def find_affected_image_ids(db_session):
    """Ids of images whose thumbnail or preview is missing or identical to the original bytes."""
    stmt = (
        select(JigsawImage.id)
        .where(
            or_(
                JigsawImage.thumbnail_data.is_(None),
                JigsawImage.preview_data.is_(None),
                JigsawImage.thumbnail_data == JigsawImage.image_data,
                JigsawImage.preview_data == JigsawImage.image_data,
            )
        )
        .order_by(JigsawImage.id)
    )
    return [int(image_id) for image_id in db_session.execute(stmt).scalars()]


def regenerate_image_derivatives(db_session, image_ids, *, dry_run=False):
    """Rebuild derivatives for the given images. Returns a summary dict."""
    summary = {"checked": 0, "regenerated": 0, "unchanged": 0, "undecodable": [], "dry_run": bool(dry_run)}
    for image_id in image_ids:
        image = db_session.get(JigsawImage, image_id)
        if image is None:
            continue
        summary["checked"] += 1
        variants = api_routes._build_image_variants(image.image_data, image.mime_type)
        if variants["thumbnail_data"] is None or variants["preview_data"] is None:
            # Not a decodable image: leave derivatives empty so guests get 404, never the original.
            summary["undecodable"].append(image_id)
        changed = (
            variants["thumbnail_data"] != image.thumbnail_data
            or variants["preview_data"] != image.preview_data
        )
        if not changed:
            summary["unchanged"] += 1
            db_session.expunge(image)
            continue
        summary["regenerated"] += 1
        if dry_run:
            db_session.expunge(image)
            continue
        image.thumbnail_mime_type = variants["thumbnail_mime_type"]
        image.thumbnail_data = variants["thumbnail_data"]
        image.preview_mime_type = variants["preview_mime_type"]
        image.preview_data = variants["preview_data"]
        image.content_version = api_routes._normalize_image_content_version(image.content_version) + 1
        db_session.commit()
        db_session.expunge(image)

    if not dry_run and summary["regenerated"]:
        db_session.add(
            AuditEvent(
                actor_user_id=None,
                action=AUDIT_ACTION,
                entity_type="jigsaw_image",
                entity_id="bulk",
                request_id="script_regenerate_image_derivatives",
                payload_json=json.dumps(
                    {
                        "checked": summary["checked"],
                        "regenerated": summary["regenerated"],
                        "unchanged": summary["unchanged"],
                        "undecodable_image_ids": summary["undecodable"],
                    },
                    sort_keys=True,
                ),
            )
        )
        db_session.commit()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db_session = get_session()
        image_ids = find_affected_image_ids(db_session)
        print(f"Images with missing or original-bytes derivatives: {len(image_ids)}")
        summary = regenerate_image_derivatives(db_session, image_ids, dry_run=args.dry_run)

    verb = "Would regenerate" if args.dry_run else "Regenerated"
    print(f"{verb}: {summary['regenerated']}  unchanged: {summary['unchanged']}  checked: {summary['checked']}")
    if summary["undecodable"]:
        print(f"Not decodable (derivatives left empty, hidden from guests): {summary['undecodable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
