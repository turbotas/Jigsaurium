from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text


@pytest.mark.functional
def test_alembic_upgrade_and_downgrade_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "migration_smoke.db"

    alembic_cfg = AlembicConfig(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()
    assert "roles" in inspector.get_table_names()
    assert "jigsaws" in inspector.get_table_names()

    with engine.connect() as connection:
        role_names = [
            row[0]
            for row in connection.execute(
                text("SELECT name FROM roles WHERE name IN ('administrator', 'borrower') ORDER BY name")
            )
        ]
    assert role_names == ["administrator", "borrower"]

    command.downgrade(alembic_cfg, "base")

    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
    engine.dispose()


@pytest.mark.functional
def test_alembic_upgrade_fails_fast_when_database_url_is_implicit(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]

    monkeypatch.setenv("DATABASE_URL", "")

    alembic_cfg = AlembicConfig(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "migrations"))

    with pytest.raises(RuntimeError, match="Alembic is targeting in-memory SQLite"):
        command.upgrade(alembic_cfg, "head")
