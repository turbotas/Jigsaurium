import argparse
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app import create_app
from app.db import get_engine, get_session
from app.models import Jigsaw, JigsawDiaryEntry, JigsawImage, Loan, Role, User, UserRole
from app.models.jigsaw import JigsawStatus
from app.models.loan import LoanStatus
from scripts.reset_demo_data import reset_application_data


def _parse_args():
    parser = argparse.ArgumentParser(description="Seed evaluator/demo data.")
    parser.add_argument(
        "--password",
        required=True,
        help="Password to apply to all demo users (minimum 12 chars)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for this command only",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env-style file to load before seeding",
    )
    parser.add_argument(
        "--reset-first",
        action="store_true",
        help="Clear existing mutable app data before inserting demo records",
    )
    return parser.parse_args()


def _load_env_file(env_file, overwrite=False):
    file_path = Path(env_file)
    if not file_path.exists():
        print(f"Error: env file does not exist: {env_file}", file=sys.stderr)
        raise SystemExit(1)

    if load_dotenv is not None:
        load_dotenv(dotenv_path=file_path, override=overwrite)
        return

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if value.startswith(('"', "'")) and value.endswith(('"', "'")) and len(value) >= 2:
            value = value[1:-1]

        if overwrite or key not in os.environ:
            os.environ[key] = value


def _load_runtime_environment(env_file):
    if env_file is not None:
        _load_env_file(env_file, overwrite=True)
        return

    default_env_file = REPO_ROOT / ".env"
    if default_env_file.exists():
        _load_env_file(str(default_env_file), overwrite=False)


def _validate_database_ready(app):
    database_url = app.config.get("DATABASE_URL", "")
    if ":memory:" in database_url:
        print(
            "Error: DATABASE_URL points to an in-memory database. "
            "Set DATABASE_URL to your real dev/test/prod database before seeding demo data.",
            file=sys.stderr,
        )
        return False

    engine = get_engine(app)
    inspector = inspect(engine)
    required_tables = {"roles", "users", "jigsaws", "jigsaw_images", "jigsaw_diary_entries", "loans"}
    existing_tables = set(inspector.get_table_names())
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        print(
            "Error: database schema is not ready. Missing tables: "
            f"{', '.join(missing_tables)}. Run `alembic upgrade head` first.",
            file=sys.stderr,
        )
        return False

    return True


def _ensure_default_roles(db_session):
    desired = {
        "administrator": "Full administrative access",
        "member": "Shared collection contributor",
        "borrower": "Legacy compatibility role",
    }
    existing = {
        str(role.name): role
        for role in db_session.query(Role).all()
    }

    roles = {}
    for role_name, description in desired.items():
        role = existing.get(role_name)
        if role is None:
            role = Role(name=role_name, description=description)
            db_session.add(role)
            db_session.flush()
        elif not role.description:
            role.description = description
        roles[role_name] = role
    return roles


def _upsert_user(db_session, *, email, display_name, password, role):
    normalized_email = str(email).strip().lower()
    user = db_session.query(User).filter_by(email=normalized_email).one_or_none()
    if user is None:
        user = User(email=normalized_email, display_name=display_name, is_active=True)
        db_session.add(user)
        db_session.flush()

    user.display_name = display_name
    user.is_active = True
    user.set_password(password)

    role_link = (
        db_session.query(UserRole)
        .filter_by(user_id=user.id, role_id=role.id)
        .one_or_none()
    )
    if role_link is None:
        db_session.add(UserRole(user_id=user.id, role_id=role.id))

    return user


def _upsert_jigsaw(db_session, *, title, piece_count, status, tags, description):
    jigsaw = (
        db_session.query(Jigsaw)
        .filter(Jigsaw.title == title, Jigsaw.piece_count == piece_count)
        .order_by(Jigsaw.id.asc())
        .first()
    )
    if jigsaw is None:
        jigsaw = Jigsaw(
            title=title,
            piece_count=piece_count,
            status=status,
            tags=tags,
            description=description,
        )
        db_session.add(jigsaw)
        db_session.flush()
    else:
        jigsaw.status = status
        jigsaw.tags = tags
        jigsaw.description = description
    return jigsaw


def _make_demo_png_bytes(seed_text):
    # Minimal deterministic bytes; not a valid PNG image, but sufficient for binary storage tests/demo records.
    payload = (b"\x89PNG\r\n\x1a\n" + seed_text.encode("utf-8", errors="ignore"))[:64]
    return payload + (b"d" * max(0, 64 - len(payload)))


def _ensure_image_for_jigsaw(db_session, *, jigsaw_id, tag, filename, seed_text, uploaded_by_user_id):
    existing = (
        db_session.query(JigsawImage)
        .filter_by(jigsaw_id=jigsaw_id, tag=tag, filename=filename)
        .order_by(JigsawImage.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    image_data = _make_demo_png_bytes(seed_text)
    image_sha = hashlib.sha256(image_data).hexdigest()
    image = JigsawImage(
        jigsaw_id=jigsaw_id,
        tag=tag,
        filename=filename,
        mime_type="image/png",
        image_data=image_data,
        image_sha256=image_sha,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db_session.add(image)
    db_session.flush()
    return image


def _ensure_unassigned_completed_image(db_session, *, filename, seed_text, uploaded_by_user_id):
    existing = (
        db_session.query(JigsawImage)
        .filter_by(jigsaw_id=None, tag="Completed", filename=filename)
        .order_by(JigsawImage.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    image_data = _make_demo_png_bytes(seed_text)
    image_sha = hashlib.sha256(image_data).hexdigest()
    image = JigsawImage(
        jigsaw_id=None,
        tag="Completed",
        filename=filename,
        mime_type="image/png",
        image_data=image_data,
        image_sha256=image_sha,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db_session.add(image)
    db_session.flush()
    return image


def _ensure_diary_entry(db_session, *, jigsaw_id, created_by_user_id, completed_at, difficulty, notes):
    existing = (
        db_session.query(JigsawDiaryEntry)
        .filter(
            JigsawDiaryEntry.jigsaw_id == jigsaw_id,
            JigsawDiaryEntry.created_by_user_id == created_by_user_id,
            JigsawDiaryEntry.notes == notes,
        )
        .order_by(JigsawDiaryEntry.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    entry = JigsawDiaryEntry(
        jigsaw_id=jigsaw_id,
        created_by_user_id=created_by_user_id,
        completed_at=completed_at,
        difficulty=difficulty,
        notes=notes,
    )
    db_session.add(entry)
    db_session.flush()
    return entry


def _ensure_active_loan(db_session, *, borrower_user_id, jigsaw_id, due_at):
    existing = (
        db_session.query(Loan)
        .filter_by(borrower_user_id=borrower_user_id, jigsaw_id=jigsaw_id, status=LoanStatus.ACTIVE)
        .order_by(Loan.id.asc())
        .first()
    )
    if existing is not None:
        existing.due_at = due_at
        return existing

    loan = Loan(
        borrower_user_id=borrower_user_id,
        jigsaw_id=jigsaw_id,
        due_at=due_at,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    db_session.flush()
    return loan


def main():
    args = _parse_args()

    if len(str(args.password or "")) < 12:
        print("Error: --password must be at least 12 characters.", file=sys.stderr)
        return 1

    _load_runtime_environment(args.env_file)
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url.strip()
    os.environ["IMAGE_EMBEDDINGS_WARM_ON_STARTUP"] = "0"

    app = create_app()
    with app.app_context():
        print(f"Using DATABASE_URL: {app.config.get('DATABASE_URL', '')}")

        if not _validate_database_ready(app):
            return 1

        db_session = get_session()
        try:
            if args.reset_first:
                reset_application_data(db_session)

            roles = _ensure_default_roles(db_session)

            admin_user = _upsert_user(
                db_session,
                email="admin@example.com",
                display_name="Demo Admin",
                password=args.password,
                role=roles["administrator"],
            )
            member_user = _upsert_user(
                db_session,
                email="member@example.com",
                display_name="Demo Member",
                password=args.password,
                role=roles["member"],
            )
            borrower_user = _upsert_user(
                db_session,
                email="borrower@example.com",
                display_name="Demo Borrower",
                password=args.password,
                role=roles["borrower"],
            )

            now = datetime.now(timezone.utc)
            jigsaw_sunset = _upsert_jigsaw(
                db_session,
                title="Sunset Harbour",
                piece_count=1000,
                status=JigsawStatus.AVAILABLE,
                tags="landscape,water",
                description="Demo seed: colour-rich harbour scene.",
            )
            jigsaw_forest = _upsert_jigsaw(
                db_session,
                title="Forest Cottage",
                piece_count=500,
                status=JigsawStatus.AVAILABLE,
                tags="nature,cottage",
                description="Demo seed: cottage in woodland.",
            )
            jigsaw_city = _upsert_jigsaw(
                db_session,
                title="City Skyline",
                piece_count=750,
                status=JigsawStatus.ON_LOAN,
                tags="city,night",
                description="Demo seed: skyline at dusk.",
            )

            _ensure_image_for_jigsaw(
                db_session,
                jigsaw_id=jigsaw_sunset.id,
                tag="Box",
                filename="sunset-box.png",
                seed_text="sunset-box",
                uploaded_by_user_id=admin_user.id,
            )
            _ensure_image_for_jigsaw(
                db_session,
                jigsaw_id=jigsaw_forest.id,
                tag="Completed",
                filename="forest-completed.png",
                seed_text="forest-completed",
                uploaded_by_user_id=member_user.id,
            )
            _ensure_unassigned_completed_image(
                db_session,
                filename="orphan-completed.png",
                seed_text="orphan-completed",
                uploaded_by_user_id=member_user.id,
            )

            diary_one = _ensure_diary_entry(
                db_session,
                jigsaw_id=jigsaw_sunset.id,
                created_by_user_id=admin_user.id,
                completed_at=now - timedelta(days=10),
                difficulty=3,
                notes="Demo seed completion by admin.",
            )
            diary_two = _ensure_diary_entry(
                db_session,
                jigsaw_id=jigsaw_forest.id,
                created_by_user_id=member_user.id,
                completed_at=now - timedelta(days=4),
                difficulty=2,
                notes="Demo seed completion by member.",
            )

            jigsaw_sunset.last_completed_at = diary_one.completed_at
            jigsaw_forest.last_completed_at = diary_two.completed_at

            _ensure_active_loan(
                db_session,
                borrower_user_id=borrower_user.id,
                jigsaw_id=jigsaw_city.id,
                due_at=now + timedelta(days=14),
            )

            db_session.commit()
        except OperationalError as error:
            db_session.rollback()
            print(f"Error: failed to seed demo data: {error}", file=sys.stderr)
            return 1

        print("Demo data seed complete.")
        print("- users: admin@example.com, member@example.com, borrower@example.com")
        print("- password: (value passed to --password)")
        print("- jigsaws: Sunset Harbour, Forest Cottage, City Skyline")
        print("- includes diary entries, images, and one active loan")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
