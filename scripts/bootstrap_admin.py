import argparse
import getpass
import sys
from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

from app import create_app
from app.db import get_engine, get_session
from app.models import Role, User, UserRole


def _parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap or rotate an administrator credential.")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--display-name", default="Administrator", help="Display name for the administrator account")
    parser.add_argument("--password", default=None, help="Password value (omit to prompt securely)")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for this command only",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env-style file to load before bootstrapping",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Allow rotating password for an existing admin account",
    )
    return parser.parse_args()


def _read_password(cli_password):
    password = cli_password
    if password is None:
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise ValueError("Password confirmation did not match.")

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")
    return password


def _validate_database_ready(app):
    database_url = app.config.get("DATABASE_URL", "")
    if ":memory:" in database_url:
        print(
            "Error: DATABASE_URL points to an in-memory database. "
            "Set DATABASE_URL to your real dev/test/prod database before bootstrapping.",
            file=sys.stderr,
        )
        return False

    engine = get_engine(app)
    inspector = inspect(engine)
    required_tables = {"roles", "users", "user_roles"}
    existing_tables = set(inspector.get_table_names())
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        print(
            "Error: database schema is not ready. Missing tables: "
            f"{', '.join(missing_tables)}. Run `alembic upgrade head` first.",
            file=sys.stderr,
        )
        return False

    users_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" not in users_columns:
        print(
            "Error: users.password_hash column is missing. "
            "Run `alembic upgrade head` against the same DATABASE_URL used by this command.",
            file=sys.stderr,
        )
        return False

    return True


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


def main():
    args = _parse_args()

    _load_runtime_environment(args.env_file)
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url.strip()

    try:
        password = _read_password(args.password)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    app = create_app()
    with app.app_context():
        print(f"Using DATABASE_URL: {app.config.get('DATABASE_URL', '')}")

        if not _validate_database_ready(app):
            return 1

        db_session = get_session()

        try:
            admin_role = db_session.query(Role).filter_by(name="administrator").one_or_none()
        except OperationalError:
            print(
                "Error: failed to read roles table. Ensure migrations are applied with `alembic upgrade head`.",
                file=sys.stderr,
            )
            return 1

        if admin_role is None:
            admin_role = Role(name="administrator", description="Full administrative access")
            db_session.add(admin_role)
            db_session.flush()

        normalized_email = args.email.strip().lower()
        try:
            user = db_session.query(User).filter_by(email=normalized_email).one_or_none()
        except OperationalError:
            print(
                "Error: failed to query users table schema. "
                "Apply latest migrations (`alembic upgrade head`) to this DATABASE_URL and try again.",
                file=sys.stderr,
            )
            return 1

        if user is None:
            user = User(email=normalized_email, display_name=args.display_name.strip() or "Administrator", is_active=True)
            user.set_password(password)
            db_session.add(user)
            db_session.flush()

            db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
            db_session.commit()
            print(f"Created administrator account for {normalized_email}.")
            return 0

        role_link = (
            db_session.query(UserRole)
            .filter_by(user_id=user.id, role_id=admin_role.id)
            .one_or_none()
        )
        if role_link is None:
            db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))

        user.is_active = True
        if args.reset_password:
            user.set_password(password)
        elif not user.password_hash:
            user.set_password(password)
        else:
            print(
                "Error: account already exists with a password. Re-run with --reset-password to rotate it.",
                file=sys.stderr,
            )
            db_session.rollback()
            return 1

        if args.display_name:
            user.display_name = args.display_name.strip() or user.display_name

        db_session.commit()
        print(f"Updated administrator account for {normalized_email}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
