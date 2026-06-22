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

    assert b"Jigsaurium Flask App" in response.data
    assert b"Your project scaffold is ready." in response.data


@pytest.mark.functional
def test_home_route_returns_html(client):
    response = client.get("/")

    assert response.content_type.startswith("text/html")
