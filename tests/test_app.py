import flask
import pytest

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

    assert b"Admin control panel" in response.data
    assert b"id=\"login-form\"" in response.data
    assert b"id=\"admin-sections\" hidden" in response.data
    assert b"/static/js/app.js" in response.data
    assert b"/mobile-capture" in response.data


@pytest.mark.functional
def test_mobile_capture_route_renders_expected_content(client):
    response = client.get("/mobile-capture")

    assert response.status_code == 200
    assert b"Mobile jigsaw capture" in response.data
    assert b"id=\"mobile-capture-login-form\"" in response.data
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
    assert payload["data"]["environment"] == "test"
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
