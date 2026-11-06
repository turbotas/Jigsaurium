import argparse
import os
import sys
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
from app.models import (
    AiUsageEvent,
    AuditEvent,
    BlockedIp,
    BulkAiCreateJob,
    BulkAiCreateJobItem,
    DatabaseBackup,
    ImageEmbedding,
    ImageEmbeddingJob,
    Jigsaw,
    JigsawDiaryEntry,
    JigsawImage,
    Loan,
    Role,
    User,
    UserRole,
    UserSession,
)


def _parse_args():
    parser = argparse.ArgumentParser(description="Reset evaluator/demo application data.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for this command only",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env-style file to load before reset",
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
            "Set DATABASE_URL to your real dev/test/prod database before resetting demo data.",
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


def reset_application_data(db_session):
    deletion_order = [
        UserSession,
        BlockedIp,
        AuditEvent,
        AiUsageEvent,
        BulkAiCreateJobItem,
        BulkAiCreateJob,
        ImageEmbedding,
        ImageEmbeddingJob,
        DatabaseBackup,
        JigsawDiaryEntry,
        Loan,
        JigsawImage,
        Jigsaw,
        UserRole,
        User,
    ]

    deleted_counts = {}
    for model in deletion_order:
        deleted_counts[model.__tablename__] = int(db_session.query(model).delete(synchronize_session=False) or 0)
    return deleted_counts


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

    created_count = 0
    for role_name, description in desired.items():
        role = existing.get(role_name)
        if role is None:
            db_session.add(Role(name=role_name, description=description))
            created_count += 1
        elif not role.description:
            role.description = description
    return created_count


def main():
    args = _parse_args()

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
            deleted_counts = reset_application_data(db_session)
            created_roles = _ensure_default_roles(db_session)
            db_session.commit()
        except OperationalError as error:
            db_session.rollback()
            print(f"Error: failed to reset demo data: {error}", file=sys.stderr)
            return 1

        print("Demo data reset complete.")
        for table_name in sorted(deleted_counts.keys()):
            print(f"- deleted {deleted_counts[table_name]} row(s) from {table_name}")
        print(f"- ensured default roles (created {created_roles})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
