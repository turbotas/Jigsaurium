import pytest

from app import create_app
from tests.migration_utils import upgrade_database_to_head


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "functional_test.db"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"

    class FunctionalTestConfig:
        APP_ENV = "test"
        SECRET_KEY = "functional-test-secret"
        TESTING = True
        DATABASE_URL = database_url
        LOG_LEVEL = "INFO"
        CANONICAL_HOST = "localhost"
        TRUSTED_PROXY_CIDRS = []
        TRUSTED_PROXY_HOPS = None
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
        PREFERRED_URL_SCHEME = "http"

    monkeypatch.setenv("DATABASE_URL", database_url)
    application = create_app(FunctionalTestConfig)

    upgrade_database_to_head(database_url)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()
