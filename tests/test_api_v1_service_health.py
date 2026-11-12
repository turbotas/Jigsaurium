"""Tests for POST /api/v1/system/health/probe (issue #64).

The AI transport and embedding engine are monkeypatched so these run in CI
without an AI credential or the torch/transformers runtime.
"""

import json
import math

import pytest

from app.api.v1 import routes
from app.db import get_session
from app.image_embeddings import build_model_key
from app.models import AiUsageEvent, ImageEmbedding, JigsawImage, Role, User, UserRole

PROBE_PATH = "/api/v1/system/health/probe"
CSRF = "test-csrf-token"


@pytest.fixture()
def users(app):
    with app.app_context():
        db_session = get_session()
        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        member_role = db_session.query(Role).filter_by(name="member").one()
        admin = User(email="admin@example.com", display_name="Admin")
        member = User(email="member@example.com", display_name="Member")
        admin.set_password("AdminPassword123!")
        member.set_password("MemberPassword123!")
        db_session.add_all([admin, member])
        db_session.flush()
        db_session.add_all(
            [
                UserRole(user_id=admin.id, role_id=admin_role.id),
                UserRole(user_id=member.id, role_id=member_role.id),
            ]
        )
        db_session.commit()
        return {"admin": admin.id, "member": member.id}


@pytest.fixture()
def ai_configured(app):
    app.config.update(
        AI_ENABLED=True,
        AI_API_KEY="test-key",
        AI_ENDPOINT_URL="https://ai.example.test/v1/chat/completions",
        AI_MODEL="test-model",
    )


@pytest.fixture()
def embeddings_enabled(app, monkeypatch):
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = True
    monkeypatch.setattr(routes, "embedding_runtime_error", lambda: None)
    monkeypatch.setattr(routes, "is_embedding_model_loaded", lambda: True)


def _login(client, user_id):
    with client.session_transaction() as test_session:
        test_session["user_id"] = user_id
        test_session["csrf_token"] = CSRF


def _probe(client, body=None):
    return client.post(PROBE_PATH, json=body if body is not None else {}, headers={"X-CSRF-Token": CSRF})


def _fake_ai_response(content='{"ok": true}', usage=None):
    return json.dumps(
        {
            "choices": [{"message": {"content": content}}],
            "usage": usage or {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
        }
    )


def _unit_vector(dim):
    value = 1.0 / math.sqrt(dim)
    return [value] * dim


@pytest.mark.functional
def test_probe_requires_authentication(client):
    response = client.post(PROBE_PATH, json={})
    assert response.status_code == 401


@pytest.mark.functional
def test_probe_forbidden_for_non_admin(client, users):
    _login(client, users["member"])
    response = _probe(client)
    assert response.status_code == 403


@pytest.mark.functional
def test_probe_reports_disabled_services(client, users):
    _login(client, users["admin"])
    response = _probe(client)

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["probes"]["ai"]["status"] == "disabled"
    assert data["probes"]["image_embeddings"]["status"] == "disabled"
    assert data["overall_status"] == "ok"


@pytest.mark.functional
def test_ai_probe_down_when_enabled_but_not_configured(app, client, users):
    app.config["AI_ENABLED"] = True
    _login(client, users["admin"])

    data = _probe(client, {"probes": ["ai"]}).get_json()["data"]

    assert data["probes"]["ai"]["status"] == "down"
    assert data["probes"]["ai"]["error_code"] == "not_configured"
    assert data["overall_status"] == "down"


@pytest.mark.functional
def test_ai_probe_success_records_usage_event(app, client, users, ai_configured, monkeypatch):
    captured = {}

    def fake_post(**kwargs):
        captured.update(kwargs)
        return _fake_ai_response()

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)
    _login(client, users["admin"])

    data = _probe(client, {"probes": ["ai"]}).get_json()["data"]

    ai = data["probes"]["ai"]
    assert ai["status"] == "ok"
    assert ai["cached"] is False
    assert isinstance(ai["latency_ms"], int)
    assert ai["details"]["model"] == "test-model"
    assert ai["details"]["endpoint_host"] == "ai.example.test"
    assert ai["details"]["total_tokens"] == 25
    assert "test-key" not in json.dumps(data)
    assert captured["request_payload"]["model"] == "test-model"
    assert captured["api_key"] == "test-key"

    with app.app_context():
        events = get_session().query(AiUsageEvent).filter_by(operation="health_probe").all()
        assert len(events) == 1
        assert events[0].status == "success"
        assert events[0].image_id is None
        assert events[0].total_tokens == 25


@pytest.mark.functional
def test_ai_probe_http_error_reports_down(app, client, users, ai_configured, monkeypatch):
    def fake_post(**kwargs):
        raise routes.AiProviderRequestError("AI provider returned HTTP 401: bad key", status_code=401)

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)
    _login(client, users["admin"])

    ai = _probe(client, {"probes": ["ai"]}).get_json()["data"]["probes"]["ai"]

    assert ai["status"] == "down"
    assert ai["error_code"] == "http_401"
    assert ai["details"]["http_status"] == 401
    with app.app_context():
        event = get_session().query(AiUsageEvent).filter_by(operation="health_probe").one()
        assert event.status == "error"
        assert event.error_code == "http_401"


@pytest.mark.functional
def test_ai_probe_timeout_reports_down(client, users, ai_configured, monkeypatch):
    def fake_post(**kwargs):
        raise routes.AiProviderRequestError("AI provider request failed: timed out")

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)
    _login(client, users["admin"])

    ai = _probe(client, {"probes": ["ai"]}).get_json()["data"]["probes"]["ai"]

    assert ai["status"] == "down"
    assert ai["error_code"] == "request_failed"


@pytest.mark.functional
def test_ai_probe_unexpected_answer_reports_degraded(client, users, ai_configured, monkeypatch):
    monkeypatch.setattr(routes, "_post_ai_chat_completion", lambda **kwargs: _fake_ai_response("I can't do that"))
    _login(client, users["admin"])

    data = _probe(client, {"probes": ["ai"]}).get_json()["data"]

    assert data["probes"]["ai"]["status"] == "degraded"
    assert data["probes"]["ai"]["error_code"] == "unexpected_response"
    assert data["overall_status"] == "degraded"


@pytest.mark.functional
def test_probe_results_are_cached_until_forced(client, users, ai_configured, monkeypatch):
    calls = []

    def fake_post(**kwargs):
        calls.append(1)
        return _fake_ai_response()

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)
    _login(client, users["admin"])

    first = _probe(client, {"probes": ["ai"]}).get_json()["data"]["probes"]["ai"]
    second = _probe(client, {"probes": ["ai"]}).get_json()["data"]["probes"]["ai"]
    forced = _probe(client, {"probes": ["ai"], "force": True}).get_json()["data"]["probes"]["ai"]

    assert first["cached"] is False
    assert second["cached"] is True
    assert forced["cached"] is False
    assert len(calls) == 2


@pytest.mark.functional
def test_embedding_probe_success(client, users, embeddings_enabled, monkeypatch):
    seen = {}

    def fake_compute(image_bytes, **kwargs):
        seen["bytes"] = image_bytes
        seen["kwargs"] = kwargs
        return _unit_vector(512)

    monkeypatch.setattr(routes, "compute_image_embedding", fake_compute)
    _login(client, users["admin"])

    probe = _probe(client, {"probes": ["image_embeddings"]}).get_json()["data"]["probes"]["image_embeddings"]

    assert probe["status"] == "ok"
    assert probe["details"]["vector_dim"] == 512
    assert probe["details"]["vector_norm"] == pytest.approx(1.0)
    assert seen["bytes"].startswith(b"\x89PNG\r\n\x1a\n")
    # The health probe must exercise the real engine, never the test fallback.
    assert seen["kwargs"]["allow_test_fallback"] is False


@pytest.mark.functional
def test_embedding_probe_down_when_runtime_missing(app, client, users, monkeypatch):
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = True
    monkeypatch.setattr(routes, "embedding_runtime_error", lambda: "No module named 'torch'")
    _login(client, users["admin"])

    data = _probe(client, {"probes": ["image_embeddings"]}).get_json()["data"]

    assert data["probes"]["image_embeddings"]["status"] == "down"
    assert data["probes"]["image_embeddings"]["error_code"] == "runtime_unavailable"
    assert data["overall_status"] == "down"


@pytest.mark.functional
def test_embedding_probe_down_when_inference_fails(client, users, embeddings_enabled, monkeypatch):
    def fake_compute(image_bytes, **kwargs):
        raise RuntimeError("Image embedding model could not be loaded.")

    monkeypatch.setattr(routes, "compute_image_embedding", fake_compute)
    _login(client, users["admin"])

    probe = _probe(client, {"probes": ["image_embeddings"]}).get_json()["data"]["probes"]["image_embeddings"]

    assert probe["status"] == "down"
    assert probe["error_code"] == "inference_failed"
    assert "could not be loaded" in probe["error_message"]


@pytest.mark.functional
def test_embedding_probe_degraded_on_dimension_mismatch(app, client, users, embeddings_enabled, monkeypatch):
    monkeypatch.setattr(routes, "compute_image_embedding", lambda image_bytes, **kwargs: _unit_vector(256))
    with app.app_context():
        db_session = get_session()
        model_key = build_model_key(app.config["IMAGE_EMBEDDING_MODEL_NAME"], app.config["IMAGE_EMBEDDING_MODEL_REVISION"])
        image = JigsawImage(tag="untagged", image_data=b"x", mime_type="image/png", filename="a.png")
        db_session.add(image)
        db_session.flush()
        db_session.add(
            ImageEmbedding(
                image_id=image.id,
                model_key=model_key,
                vector_json=json.dumps(_unit_vector(512)),
                vector_dim=512,
                source_content_sha256="0" * 64,
            )
        )
        db_session.commit()
    _login(client, users["admin"])

    probe = _probe(client, {"probes": ["image_embeddings"]}).get_json()["data"]["probes"]["image_embeddings"]

    assert probe["status"] == "degraded"
    assert probe["error_code"] == "dimension_mismatch"
    assert probe["details"]["stored_vector_dims"] == [512]


@pytest.mark.functional
@pytest.mark.parametrize(
    "body",
    [
        {"force": "yes"},
        {"probes": []},
        {"probes": ["nope"]},
        {"probes": "ai"},
    ],
)
def test_probe_validates_payload(client, users, body):
    _login(client, users["admin"])
    response = _probe(client, body)
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


def test_reference_png_is_valid_image():
    png = routes._build_health_reference_png()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    from io import BytesIO

    with Image.open(BytesIO(png)) as image:
        image.load()
        assert image.size == (64, 64)
        assert image.mode == "RGB"
