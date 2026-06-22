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
