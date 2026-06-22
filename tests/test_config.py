import importlib

import pytest

import config


@pytest.mark.functional
def test_config_uses_default_secret_key_when_env_missing(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    importlib.reload(config)

    assert config.Config.SECRET_KEY == "dev-secret-key"


@pytest.mark.functional
def test_config_uses_env_secret_key_when_set(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    importlib.reload(config)

    assert config.Config.SECRET_KEY == "test-secret"

    monkeypatch.delenv("SECRET_KEY", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///jigsaurium_test.db")

    importlib.reload(config)

    assert config.Config.DATABASE_URL == "sqlite+pysqlite:///jigsaurium_test.db"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_parses_proxy_settings(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8, 192.168.0.0/16")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")

    importlib.reload(config)

    assert config.Config.TRUSTED_PROXY_CIDRS == ["10.0.0.0/8", "192.168.0.0/16"]
    assert config.Config.TRUSTED_PROXY_HOPS == 2

    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    importlib.reload(config)
