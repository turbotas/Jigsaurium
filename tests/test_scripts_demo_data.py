import subprocess
import sys
from pathlib import Path

import pytest

from app import create_app
from app.db import get_session
from app.models import Jigsaw, JigsawDiaryEntry, JigsawImage, Loan, Role, User
from tests.migration_utils import upgrade_database_to_head


def _build_test_app(database_url):
    class ScriptTestConfig:
        APP_ENV = "test"
        SECRET_KEY = "script-test-secret-0123456789abcdef"
        TESTING = True
        DATABASE_URL = database_url
        LOG_LEVEL = "INFO"
        CANONICAL_HOST = "localhost"
        TRUSTED_PROXY_CIDRS = []
        TRUSTED_PROXY_HOPS = None
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
        PREFERRED_URL_SCHEME = "http"

    return create_app(ScriptTestConfig)


@pytest.mark.functional
def test_seed_demo_data_script_populates_expected_records(tmp_path):
    db_path = tmp_path / "seed_demo.db"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    upgrade_database_to_head(database_url)

    repo_root = Path(__file__).resolve().parents[1]
    seed_script = repo_root / "scripts" / "seed_demo_data.py"
    command = [
        sys.executable,
        str(seed_script),
        "--database-url",
        database_url,
        "--password",
        "DemoPassword123!",
        "--reset-first",
    ]

    result = subprocess.run(command, capture_output=True, text=True, cwd=str(repo_root), check=False)
    assert result.returncode == 0, result.stderr or result.stdout

    app = _build_test_app(database_url)
    with app.app_context():
        db_session = get_session()
        assert db_session.query(User).count() == 3
        assert db_session.query(Role).count() >= 3
        assert db_session.query(Jigsaw).count() >= 3
        assert db_session.query(JigsawImage).count() >= 3
        assert db_session.query(JigsawDiaryEntry).count() >= 2
        assert db_session.query(Loan).count() >= 1


@pytest.mark.functional
def test_reset_demo_data_script_clears_mutable_records(tmp_path):
    db_path = tmp_path / "reset_demo.db"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    upgrade_database_to_head(database_url)

    repo_root = Path(__file__).resolve().parents[1]
    seed_script = repo_root / "scripts" / "seed_demo_data.py"
    reset_script = repo_root / "scripts" / "reset_demo_data.py"

    seed_result = subprocess.run(
        [
            sys.executable,
            str(seed_script),
            "--database-url",
            database_url,
            "--password",
            "DemoPassword123!",
            "--reset-first",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        check=False,
    )
    assert seed_result.returncode == 0, seed_result.stderr or seed_result.stdout

    reset_result = subprocess.run(
        [
            sys.executable,
            str(reset_script),
            "--database-url",
            database_url,
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        check=False,
    )
    assert reset_result.returncode == 0, reset_result.stderr or reset_result.stdout

    app = _build_test_app(database_url)
    with app.app_context():
        db_session = get_session()
        assert db_session.query(User).count() == 0
        assert db_session.query(Jigsaw).count() == 0
        assert db_session.query(JigsawImage).count() == 0
        assert db_session.query(JigsawDiaryEntry).count() == 0
        assert db_session.query(Loan).count() == 0
        assert db_session.query(Role).count() >= 3
