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
    monkeypatch.setenv("TRUSTED_CLIENT_CIDRS", "192.168.100.0/24, 10.10.0.0/16")

    importlib.reload(config)

    assert config.Config.TRUSTED_PROXY_CIDRS == ["10.0.0.0/8", "192.168.0.0/16"]
    assert config.Config.TRUSTED_PROXY_HOPS == 2
    assert config.Config.TRUSTED_CLIENT_CIDRS == ["192.168.100.0/24", "10.10.0.0/16"]

    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    monkeypatch.delenv("TRUSTED_CLIENT_CIDRS", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_parses_canonical_host_enforcement(monkeypatch):
    monkeypatch.setenv("CANONICAL_HOST_ENFORCEMENT", "off")

    importlib.reload(config)

    assert config.Config.CANONICAL_HOST_ENFORCEMENT == "off"

    monkeypatch.delenv("CANONICAL_HOST_ENFORCEMENT", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_invalid_canonical_host_enforcement_raises_actionable_error(monkeypatch):
    monkeypatch.setenv("CANONICAL_HOST_ENFORCEMENT", "redirect")

    with pytest.raises(ValueError, match="CANONICAL_HOST_ENFORCEMENT"):
        importlib.reload(config)

    monkeypatch.delenv("CANONICAL_HOST_ENFORCEMENT", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_invalid_trusted_proxy_hops_raises_actionable_error(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "abc")

    with pytest.raises(ValueError, match="TRUSTED_PROXY_HOPS"):
        importlib.reload(config)

    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_invalid_ai_budget_raises_actionable_error(monkeypatch):
    monkeypatch.setenv("AI_DAILY_BUDGET_USD", "not-a-number")

    with pytest.raises(ValueError, match="AI_DAILY_BUDGET_USD"):
        importlib.reload(config)

    monkeypatch.delenv("AI_DAILY_BUDGET_USD", raising=False)
    importlib.reload(config)


@pytest.mark.functional
def test_config_parses_hsts_settings(monkeypatch):
    monkeypatch.setenv("HSTS_MAX_AGE_SECONDS", "12345")
    monkeypatch.setenv("HSTS_INCLUDE_SUBDOMAINS", "0")
    monkeypatch.setenv("HSTS_PRELOAD", "1")

    importlib.reload(config)

    assert config.Config.HSTS_MAX_AGE_SECONDS == 12345
    assert config.Config.HSTS_INCLUDE_SUBDOMAINS is False
    assert config.Config.HSTS_PRELOAD is True

    monkeypatch.delenv("HSTS_MAX_AGE_SECONDS", raising=False)
    monkeypatch.delenv("HSTS_INCLUDE_SUBDOMAINS", raising=False)
    monkeypatch.delenv("HSTS_PRELOAD", raising=False)
    importlib.reload(config)
