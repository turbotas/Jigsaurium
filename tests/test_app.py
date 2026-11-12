import flask
import pytest
import re
import app as app_module

from app import create_app


@pytest.mark.functional
def test_create_app_returns_flask_instance():
    app = create_app()

    assert isinstance(app, flask.Flask)


@pytest.mark.functional
def test_main_blueprint_is_registered(app):
    assert "main" in app.blueprints


@pytest.mark.functional
def test_create_app_accepts_custom_config_object():
    class TestConfig:
        SECRET_KEY = "custom-key"
        TESTING = True

    app = create_app(TestConfig)

    assert app.config["SECRET_KEY"] == "custom-key"
    assert app.config["TESTING"] is True


@pytest.mark.functional
def test_create_app_rejects_invalid_backup_compression_value():
    class InvalidConfig:
        SECRET_KEY = "custom-key"
        TESTING = True
        DB_BACKUP_COMPRESSION = "zip"

    with pytest.raises(RuntimeError, match="DB_BACKUP_COMPRESSION"):
        create_app(InvalidConfig)


@pytest.mark.functional
def test_create_app_rejects_negative_ai_daily_budget_value():
    class InvalidConfig:
        SECRET_KEY = "custom-key"
        TESTING = True
        AI_DAILY_BUDGET_USD = -1

    with pytest.raises(RuntimeError, match="AI_DAILY_BUDGET_USD"):
        create_app(InvalidConfig)


@pytest.mark.functional
def test_create_app_rejects_default_secret_key_in_non_dev_environment():
    class InvalidConfig:
        APP_ENV = "test"
        SECRET_KEY = "dev-secret-key"
        TESTING = True

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(InvalidConfig)


@pytest.mark.functional
def test_create_app_rejects_short_secret_key_in_non_dev_environment():
    class InvalidConfig:
        APP_ENV = "prod"
        SECRET_KEY = "short-secret"
        TESTING = True

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(InvalidConfig)


@pytest.mark.functional
@pytest.mark.parametrize("secret_length, should_start", [(31, False), (32, True)])
def test_create_app_requires_32_character_secret_key_in_non_dev_environment(secret_length, should_start):
    class SecretLengthConfig:
        APP_ENV = "prod"
        SECRET_KEY = "k" * secret_length
        TESTING = True
        DATABASE_URL = "sqlite+pysqlite:///:memory:"
        CANONICAL_HOST = "localhost"

    if should_start:
        assert create_app(SecretLengthConfig).config["SECRET_KEY"] == "k" * secret_length
    else:
        with pytest.raises(RuntimeError, match="at least 32"):
            create_app(SecretLengthConfig)


@pytest.mark.functional
def test_create_app_allows_default_secret_key_in_dev_environment():
    class DevConfig:
        APP_ENV = "dev"
        SECRET_KEY = "dev-secret-key"
        TESTING = True

    app = create_app(DevConfig)
    assert app.config["SECRET_KEY"] == "dev-secret-key"


@pytest.mark.functional
def test_create_app_skips_missing_local_embedding_model_on_dev_startup(monkeypatch):
    def _raise_missing_model(*_args, **_kwargs):
        raise RuntimeError("Configured embedding model path does not exist: .hf-models/clip-vit-base-patch32")

    monkeypatch.setattr(app_module, "warm_embedding_runtime", _raise_missing_model)

    class DevConfig:
        APP_ENV = "dev"
        SECRET_KEY = "dev-secret-key"
        TESTING = True
        IMAGE_EMBEDDINGS_ENABLED = True
        IMAGE_EMBEDDINGS_WARM_ON_STARTUP = True
        IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR = True
        IMAGE_EMBEDDING_MODEL_LOCAL_PATH = ".hf-models/clip-vit-base-patch32"

    app = create_app(DevConfig)

    assert app.config["IMAGE_EMBEDDINGS_ENABLED"] is True


@pytest.mark.functional
def test_create_app_keeps_fail_fast_missing_local_embedding_model_outside_dev(monkeypatch):
    def _raise_missing_model(*_args, **_kwargs):
        raise RuntimeError("Configured embedding model path does not exist: /opt/models/clip-vit-base-patch32")

    monkeypatch.setattr(app_module, "warm_embedding_runtime", _raise_missing_model)

    class TestConfig:
        APP_ENV = "test"
        SECRET_KEY = "this-is-a-long-enough-test-secret"
        TESTING = True
        IMAGE_EMBEDDINGS_ENABLED = True
        IMAGE_EMBEDDINGS_WARM_ON_STARTUP = True
        IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR = True
        IMAGE_EMBEDDING_MODEL_LOCAL_PATH = "/opt/models/clip-vit-base-patch32"

    with pytest.raises(RuntimeError, match="Configured embedding model path does not exist"):
        create_app(TestConfig)


@pytest.mark.functional
def test_home_route_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200


@pytest.mark.functional
def test_unknown_route_returns_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404


@pytest.mark.functional
def test_home_route_renders_expected_content(client):
    response = client.get("/")

    assert b"Jigsaurium Main Page" in response.data
    assert b"id=\"login-form\"" in response.data
    assert b"id=\"workspace-tabs\"" in response.data
    assert b"id=\"mobile-upload-nav-button\"" in response.data
    assert b"data-workspace-tab=\"collection\"" in response.data
    assert b"Filter jigsaws" in response.data
    assert b"id=\"jigsaws-pagination-top\"" in response.data
    assert b"Show all images" in response.data
    assert b"id=\"jigsaw-detail-modal\"" in response.data
    assert b"id=\"jigsaw-detail-images-body\"" in response.data
    assert b"id=\"admin-sections\" hidden" in response.data
    assert b"id=\"image-editor-context\"" in response.data
    assert b"data-enabled=\"0\"" in response.data
    assert b"data-feature-ai-enabled=\"" in response.data
    assert b"data-feature-embeddings-enabled=\"" in response.data
    assert b"/static/js/app.js" in response.data
    assert b"/mobile-capture" in response.data


@pytest.mark.functional
def test_image_editor_route_renders_home_in_editor_mode(client):
    response = client.get("/image-editor/42")

    assert response.status_code == 200
    assert b"id=\"image-editor-context\"" in response.data
    assert b"data-enabled=\"1\"" in response.data
    assert b"data-image-id=\"42\"" in response.data
    assert b"data-feature-ai-enabled=\"" in response.data
    assert b"data-feature-embeddings-enabled=\"" in response.data


@pytest.mark.functional
def test_home_route_exposes_feature_flag_data_attributes(app, client):
    app.config["AI_ENABLED"] = True
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = False

    response = client.get("/")
    assert response.status_code == 200
    assert b"data-feature-ai-enabled=\"1\"" in response.data
    assert b"data-feature-embeddings-enabled=\"0\"" in response.data


@pytest.mark.functional
def test_mobile_capture_route_renders_expected_content(client):
    response = client.get("/mobile-capture")

    assert response.status_code == 200
    assert b"Mobile jigsaw capture" in response.data
    assert b"id=\"mobile-capture-sign-out-controls\"" in response.data
    assert b"id=\"mobile-capture-auth-card\"" in response.data
    assert b"id=\"mobile-capture-login-form\"" in response.data
    assert b"id=\"mobile-capture-stfd-login-button\"" in response.data
    assert b"id=\"mobile-capture-auth-mode-hint\"" in response.data
    assert b"id=\"mobile-intake-form\"" in response.data
    assert b"id=\"mobile-intake-comment\"" in response.data
    assert b"/static/js/mobile-intake.js" in response.data


@pytest.mark.functional
def test_home_route_returns_html(client):
    response = client.get("/")

    assert response.content_type.startswith("text/html")


@pytest.mark.functional
def test_api_health_returns_contract_shape(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["data"]["status"] == "ok"
    assert list(payload["data"].keys()) == ["status"]
    assert payload["meta"]["request_id"].startswith("req_")


@pytest.mark.functional
def test_security_headers_are_present_on_html_and_api_responses(client):
    home_response = client.get("/")
    api_response = client.get("/api/v1/health")

    for response in (home_response, api_response):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        assert "script-src 'self' 'nonce-" in response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" not in response.headers["Content-Security-Policy"]


@pytest.mark.functional
def test_home_route_applies_nonce_to_inline_scripts(client):
    response = client.get("/")

    html = response.get_data(as_text=True)
    assert "<script nonce=\"" in html


@pytest.mark.functional
def test_hsts_header_present_for_https_in_non_dev(client):
    response = client.get("/", base_url="https://localhost")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.functional
def test_hsts_header_absent_for_http(client):
    response = client.get("/", base_url="http://localhost")

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.functional
def test_hsts_header_uses_trusted_forwarded_proto(client, app):
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.100.0/24"]
    headers = {"X-Forwarded-Proto": "https"}

    response = client.get(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": "192.168.100.12"},
    )

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.functional
def test_hsts_header_ignores_untrusted_forwarded_proto(client, app):
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.100.0/24"]
    headers = {"X-Forwarded-Proto": "https"}

    response = client.get(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": "198.51.100.20"},
    )

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.functional
def test_home_route_uses_request_scoped_static_asset_version_in_test_env(client):
    first_response = client.get("/")
    second_response = client.get("/")

    first_html = first_response.get_data(as_text=True)
    second_html = second_response.get_data(as_text=True)

    first_match = re.search(r"/static/js/app\.js\?v=(req_[a-f0-9]{12})", first_html)
    second_match = re.search(r"/static/js/app\.js\?v=(req_[a-f0-9]{12})", second_html)

    assert first_match is not None
    assert second_match is not None
    assert first_match.group(1) != second_match.group(1)


@pytest.mark.functional
def test_static_assets_disable_cache_in_test_env(client):
    response = client.get("/static/js/app.js")

    assert response.status_code == 200
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert response.headers.get("Pragma") == "no-cache"
