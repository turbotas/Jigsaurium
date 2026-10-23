from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import zipfile

import pytest
from sqlalchemy.exc import OperationalError

from app.api.v1 import routes
from app.db import get_session
from app import image_embeddings as image_embeddings_module
from app.models import AiUsageEvent, ImageEmbedding, Jigsaw, JigsawDiaryEntry, JigsawImage, Role, User, UserRole
from app.models.jigsaw import JigsawStatus
from PIL import Image


@pytest.fixture()
def seeded_image_library_data(app):
    with app.app_context():
        db_session = get_session()

        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        borrower_role = db_session.query(Role).filter_by(name="borrower").one()

        admin_user = User(email="admin@example.com", display_name="Admin User")
        borrower_user = User(email="borrower@example.com", display_name="Borrower User")
        admin_user.set_password("AdminPassword123!")
        borrower_user.set_password("BorrowerPassword123!")
        db_session.add_all([admin_user, borrower_user])
        db_session.flush()

        db_session.add_all(
            [
                UserRole(user_id=admin_user.id, role_id=admin_role.id),
                UserRole(user_id=borrower_user.id, role_id=borrower_role.id),
            ]
        )

        jigsaw = Jigsaw(
            title="Library Puzzle",
            piece_count=1000,
            status=JigsawStatus.AVAILABLE,
        )
        db_session.add(jigsaw)
        db_session.flush()
        db_session.commit()

        seeded_ids = {
            "admin_user_id": admin_user.id,
            "borrower_user_id": borrower_user.id,
            "jigsaw_id": jigsaw.id,
        }

    db_session.remove()
    yield seeded_ids


def _set_user_session(client, user_id, csrf_token="test-csrf-token"):
    with client.session_transaction() as test_session:
        test_session["user_id"] = user_id
        test_session["csrf_token"] = csrf_token


def _csrf_headers(csrf_token="test-csrf-token"):
    return {"X-CSRF-Token": csrf_token}


def _make_zip_file(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, data in entries:
            archive.writestr(filename, data)
    output.seek(0)
    return output


def _make_png_bytes(color=(64, 64, 64), size=(24, 24)):
    output = BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()


@pytest.fixture()
def embedding_test_fallback(monkeypatch):
    monkeypatch.setattr(routes, "embedding_runtime_error", lambda: None)

    def _compute(image_bytes, *, model_name, model_revision, allow_test_fallback=False):
        return image_embeddings_module._compute_test_fallback_embedding(image_bytes)

    monkeypatch.setattr(routes, "compute_image_embedding", _compute)


@pytest.mark.functional
@pytest.mark.parametrize(
    ("method", "path", "content_type", "json_payload"),
    [
        ("GET", "/api/v1/image-library/images", None, None),
        ("POST", "/api/v1/image-library/uploads", "multipart/form-data", None),
        ("POST", "/api/v1/image-library/bulk-create-jigsaws", None, {"image_ids": [1]}),
        ("POST", "/api/v1/image-library/bulk-create-jigsaws/unassigned-box", None, {}),
        ("GET", "/api/v1/image-library/bulk-create-jigsaws/1", None, None),
        ("GET", "/api/v1/image-library/bulk-create-jigsaws/1/items", None, None),
        ("PATCH", "/api/v1/image-library/images/1/assign", None, {"jigsaw_id": 1}),
        ("PATCH", "/api/v1/image-library/images/1/tag", None, {"tag": "Box"}),
        ("DELETE", "/api/v1/image-library/images/1", None, None),
        ("POST", "/api/v1/image-embeddings/backfill", None, {}),
        ("GET", "/api/v1/image-embeddings/backfill/1", None, None),
        ("GET", "/api/v1/image-library/images/1/match-suggestions", None, None),
        ("GET", "/api/v1/images/1/content", None, None),
    ],
)
def test_image_library_endpoints_require_authentication(
    client, seeded_image_library_data, method, path, content_type, json_payload
):
    if method == "POST" and content_type == "multipart/form-data":
        response = client.open(
            path,
            method=method,
            data={"files": (BytesIO(b"\x89PNG\r\n\x1a\n"), "one.png", "image/png")},
            content_type=content_type,
        )
    elif method in {"PATCH", "POST"} and json_payload is not None:
        response = client.open(path, method=method, json=json_payload)
    else:
        response = client.open(path, method=method)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


@pytest.mark.functional
def test_borrower_cannot_use_image_library_admin_endpoints(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["borrower_user_id"])

    list_response = client.get("/api/v1/image-library/images")
    assert list_response.status_code == 403

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={"files": (BytesIO(b"\x89PNG\r\n\x1a\n"), "one.png", "image/png")},
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 403

    bulk_create_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws",
        headers=_csrf_headers(),
        json={"image_ids": [1]},
    )
    assert bulk_create_response.status_code == 403


@pytest.mark.functional
def test_image_library_upload_rejects_svg_files(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={"files": (BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"), "vector.svg", "image/svg+xml")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "files"
    assert payload["error"]["details"][0]["issue"] == "must be a supported image type or zip file"

    _set_user_session(client, seeded_image_library_data["borrower_user_id"])

    bulk_create_unassigned_box_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws/unassigned-box",
        headers=_csrf_headers(),
        json={},
    )
    assert bulk_create_unassigned_box_response.status_code == 403

    bulk_status_response = client.get("/api/v1/image-library/bulk-create-jigsaws/1")
    assert bulk_status_response.status_code == 403

    bulk_items_response = client.get("/api/v1/image-library/bulk-create-jigsaws/1/items")
    assert bulk_items_response.status_code == 403

    assign_response = client.patch(
        "/api/v1/image-library/images/1/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": seeded_image_library_data["jigsaw_id"]},
    )
    assert assign_response.status_code == 403

    tag_response = client.patch(
        "/api/v1/image-library/images/1/tag",
        headers=_csrf_headers(),
        json={"tag": "Box"},
    )
    assert tag_response.status_code == 403

    delete_response = client.delete(
        "/api/v1/image-library/images/1",
        headers=_csrf_headers(),
    )
    assert delete_response.status_code in {403, 404}

    enrich_response = client.post(
        f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/enrich-from-images",
        headers=_csrf_headers(),
        json={},
    )
    assert enrich_response.status_code == 403

    diagnostics_response = client.get("/api/v1/ai-usage/diagnostics")
    assert diagnostics_response.status_code == 403

    backfill_response = client.post(
        "/api/v1/image-embeddings/backfill",
        headers=_csrf_headers(),
        json={},
    )
    assert backfill_response.status_code == 403

    backfill_job_response = client.get("/api/v1/image-embeddings/backfill/1")
    assert backfill_job_response.status_code == 403

    suggest_response = client.get("/api/v1/image-library/images/1/match-suggestions")
    assert suggest_response.status_code == 403


@pytest.mark.functional
def test_admin_can_run_image_embedding_backfill_job(client, seeded_image_library_data, app, embedding_test_fallback):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = True
    app.config["IMAGE_EMBEDDINGS_INLINE"] = True
    app.config["IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK"] = True

    first_png = _make_png_bytes(color=(150, 20, 20))
    second_png = _make_png_bytes(color=(20, 20, 150))
    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (BytesIO(first_png), "embed-one.png", "image/png"),
                (BytesIO(second_png), "embed-two.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    create_response = client.post(
        "/api/v1/image-embeddings/backfill",
        headers=_csrf_headers(),
        json={},
    )
    assert create_response.status_code == 202
    job = create_response.get_json()["data"]["job"]
    assert job["id"]

    status_response = client.get(f"/api/v1/image-embeddings/backfill/{job['id']}")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()["data"]["job"]
    assert status_payload["status"] == "completed"
    assert status_payload["succeeded_items"] >= 2

    with app.app_context():
        db_session = get_session()
        embedding_count = db_session.query(ImageEmbedding).count()
        assert embedding_count >= 2


@pytest.mark.functional
def test_refresh_image_embedding_retries_retryable_db_errors(
    client, seeded_image_library_data, app, monkeypatch, embedding_test_fallback
):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = True
    app.config["IMAGE_EMBEDDINGS_INLINE"] = True
    app.config["IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK"] = True

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(_make_png_bytes(color=(90, 90, 90))), "retry-test.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    original_upsert = routes._upsert_image_embedding_for_image
    calls = {"count": 0}

    class _FakeMysqlError(Exception):
        def __init__(self, errno, message):
            self.args = (errno, message)

    def flaky_upsert(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OperationalError(
                statement="INSERT INTO image_embeddings (...) VALUES (...)",
                params={},
                orig=_FakeMysqlError(1020, "Record has changed since last read"),
            )
        return original_upsert(*args, **kwargs)

    monkeypatch.setattr(routes, "_upsert_image_embedding_for_image", flaky_upsert)

    with app.app_context():
        db_session = get_session()
        model_name, model_revision, model_key = routes._get_embedding_model_config()
        refreshed = routes._refresh_image_embedding_with_retry(
            db_session,
            image_id=image_id,
            model_name=model_name,
            model_revision=model_revision,
            model_key=model_key,
            allow_test_fallback=True,
            max_attempts=3,
        )
        db_session.commit()

        assert refreshed is not None
        assert calls["count"] == 2
        embedding = (
            db_session.query(ImageEmbedding)
            .filter(ImageEmbedding.image_id == image_id, ImageEmbedding.model_key == model_key)
            .one_or_none()
        )
        assert embedding is not None


@pytest.mark.functional
def test_admin_can_store_image_library_comment(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "comment": "Photo taken in low light; please verify AI title.",
            "files": [(BytesIO(_make_png_bytes(color=(20, 120, 20))), "commented-upload.png", "image/png")],
            "tag": "Box",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["created_count"] == 1
    assert payload["created"][0]["user_comment"] == "Photo taken in low light; please verify AI title."

    with app.app_context():
        db_session = get_session()
        image_id = int(payload["created"][0]["id"])
        image = db_session.get(JigsawImage, image_id)
        assert image is not None
        assert image.user_comment == "Photo taken in low light; please verify AI title."


@pytest.mark.functional
def test_completed_image_comment_is_used_for_auto_diary_notes(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    jigsaw_id = seeded_image_library_data["jigsaw_id"]

    upload_response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "Completed",
            "comment": "Finished with family over the weekend.",
            "image": (BytesIO(_make_png_bytes(color=(120, 20, 120))), "completed-comment.png", "image/png"),
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    with app.app_context():
        db_session = get_session()
        entry = (
            db_session.query(JigsawDiaryEntry)
            .filter(JigsawDiaryEntry.jigsaw_id == jigsaw_id)
            .order_by(JigsawDiaryEntry.id.desc())
            .first()
        )
        assert entry is not None
        assert entry.notes == "Finished with family over the weekend."


@pytest.mark.functional
def test_admin_can_get_visual_match_suggestions_for_unassigned_completed_image(
    client, seeded_image_library_data, app, embedding_test_fallback
):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    app.config["IMAGE_EMBEDDINGS_ENABLED"] = True
    app.config["IMAGE_EMBEDDINGS_INLINE"] = True
    app.config["IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK"] = True

    reference_png = _make_png_bytes(color=(210, 80, 30), size=(32, 32))
    upload_reference = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "tag": "Box front",
            "files": [(BytesIO(reference_png), "box-front.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_reference.status_code == 201

    completed_png = _make_png_bytes(color=(200, 70, 35), size=(32, 32))
    upload_completed = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "Completed",
            "files": [(BytesIO(completed_png), "completed.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_completed.status_code == 201
    completed_image_id = upload_completed.get_json()["data"]["created"][0]["id"]

    suggestions_response = client.get(f"/api/v1/image-library/images/{completed_image_id}/match-suggestions?limit=3")
    assert suggestions_response.status_code == 200
    payload = suggestions_response.get_json()["data"]
    assert payload["model_key"]
    assert payload["candidate_count"] >= 1
    first_candidate = payload["candidates"][0]
    assert first_candidate["jigsaw_id"] == seeded_image_library_data["jigsaw_id"]
    assert first_candidate["confidence"] in {"high", "medium", "low"}
    reference_image = first_candidate.get("reference_image") or {}
    assert reference_image.get("thumbnail_url")
    assert reference_image.get("preview_url")


@pytest.mark.functional
def test_admin_can_view_ai_usage_diagnostics(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    with app.app_context():
        db_session = get_session()
        image = JigsawImage(
            jigsaw_id=None,
            tag="untagged",
            filename="diag.png",
            mime_type="image/png",
            image_data=b"\x89PNG\r\n\x1a\n" + b"d" * 48,
        )
        db_session.add(image)
        db_session.flush()

        now = datetime.now(timezone.utc)
        events = [
            AiUsageEvent(
                actor_user_id=seeded_image_library_data["admin_user_id"],
                image_id=image.id,
                operation="image_to_jigsaw",
                status="success",
                model="mock-vision-mini",
                endpoint_url="https://example.invalid/v1/chat/completions",
                prompt_tokens=100,
                completion_tokens=20,
                total_tokens=120,
                final_cost_usd=Decimal("0.120000"),
                request_id="req_success",
                created_at=now - timedelta(minutes=30),
            ),
            AiUsageEvent(
                actor_user_id=seeded_image_library_data["admin_user_id"],
                image_id=image.id,
                operation="image_to_jigsaw",
                status="error",
                model="mock-vision-mini",
                endpoint_url="https://example.invalid/v1/chat/completions",
                prompt_tokens=80,
                completion_tokens=10,
                total_tokens=90,
                final_cost_usd=Decimal("0"),
                error_code="provider_error",
                error_message="AI provider returned HTTP 413",
                request_id="req_error",
                created_at=now - timedelta(minutes=20),
            ),
            AiUsageEvent(
                actor_user_id=seeded_image_library_data["admin_user_id"],
                image_id=image.id,
                operation="image_to_jigsaw",
                status="blocked",
                model="mock-vision-mini",
                endpoint_url="https://example.invalid/v1/chat/completions",
                total_tokens=None,
                final_cost_usd=Decimal("0"),
                error_code="daily_budget_exceeded",
                request_id="req_blocked",
                created_at=now - timedelta(minutes=10),
            ),
            AiUsageEvent(
                actor_user_id=seeded_image_library_data["admin_user_id"],
                image_id=image.id,
                operation="jigsaw_enrich_from_images",
                status="success",
                model="mock-vision-mini",
                endpoint_url="https://example.invalid/v1/chat/completions",
                prompt_tokens=210,
                completion_tokens=40,
                total_tokens=250,
                final_cost_usd=Decimal("0.230000"),
                request_id="req_old_success",
                created_at=now - timedelta(days=8),
            ),
        ]
        db_session.add_all(events)
        db_session.commit()

    response = client.get("/api/v1/ai-usage/diagnostics?limit=10")

    assert response.status_code == 200
    payload = response.get_json()["data"]

    assert payload["windows"]["today"]["calls"] == 3
    assert payload["windows"]["today"]["success"] == 1
    assert payload["windows"]["today"]["tokens"] == 210
    assert payload["windows"]["today"]["cost_usd"] == "0.120000"

    assert payload["windows"]["last_7_days"]["calls"] == 3
    assert payload["windows"]["last_30_days"]["calls"] == 4
    assert payload["windows"]["last_30_days"]["success"] == 2
    assert payload["windows"]["last_30_days"]["tokens"] == 460
    assert payload["windows"]["last_30_days"]["cost_usd"] == "0.350000"

    by_operation = {entry["operation"]: entry for entry in payload["by_operation_30d"]}
    assert by_operation["image_to_jigsaw"]["calls"] == 3
    assert by_operation["image_to_jigsaw"]["success"] == 1
    assert by_operation["image_to_jigsaw"]["tokens"] == 210
    assert by_operation["image_to_jigsaw"]["cost_usd"] == "0.120000"
    assert by_operation["jigsaw_enrich_from_images"]["calls"] == 1

    by_model = {entry["model"]: entry for entry in payload["by_model_30d"]}
    assert by_model["mock-vision-mini"]["calls"] == 4
    assert by_model["mock-vision-mini"]["success"] == 2
    assert by_model["mock-vision-mini"]["tokens"] == 460
    assert by_model["mock-vision-mini"]["cost_usd"] == "0.350000"

    recent_calls = payload["recent_calls"]
    assert len(recent_calls) == 4
    assert payload["recent_calls_pagination"]["page"] == 1
    assert payload["recent_calls_pagination"]["page_size"] == 10
    assert payload["recent_calls_pagination"]["total_items"] == 4
    assert payload["recent_calls_pagination"]["total_pages"] == 1
    error_row = next(row for row in recent_calls if row["status"] == "error")
    assert error_row["provider_http_status"] == 413
    assert error_row["error_code"] == "provider_error"
    assert error_row["image"]["filename"] == "diag.png"
    assert error_row["image"]["mime_type"] == "image/png"
    assert isinstance(error_row["image"]["size_bytes"], int)


@pytest.mark.functional
def test_admin_can_bulk_upload_multiple_unassigned_images(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"a" * 24), "first.png", "image/png"),
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"b" * 24), "second.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["created_count"] == 2
    assert payload["skipped_count"] == 0
    assert len(payload["created"]) == 2
    assert all(item["jigsaw_id"] is None for item in payload["created"])
    assert all(item["tag"] == "untagged" for item in payload["created"])

    list_response = client.get("/api/v1/image-library/images")
    assert list_response.status_code == 200
    images = list_response.get_json()["data"]
    assert len(images) >= 2


@pytest.mark.functional
def test_admin_can_fetch_jigsaw_thumbnail_images(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "tag": "Box",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 24), "thumb-source.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    response = client.get("/api/v1/jigsaws/thumbnail-images")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    matching = [item for item in payload if item["jigsaw_id"] == seeded_image_library_data["jigsaw_id"]]
    assert len(matching) >= 1
    assert matching[0]["thumbnail_url"]
    assert matching[0]["preview_url"]


@pytest.mark.functional
def test_ai_usage_diagnostics_supports_page_and_page_size(app, client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    with app.app_context():
        db_session = get_session()
        for index in range(3):
            db_session.add(
                AiUsageEvent(
                    actor_user_id=seeded_image_library_data["admin_user_id"],
                    image_id=None,
                    operation="image_to_jigsaw",
                    status="success",
                    model="mock-vision-mini",
                    endpoint_url="https://example.invalid/v1/chat/completions",
                    total_tokens=10 + index,
                    final_cost_usd=Decimal("0"),
                    request_id=f"req_page_{index}",
                )
            )
        db_session.commit()

    first_page_response = client.get("/api/v1/ai-usage/diagnostics?page=1&page_size=1")
    second_page_response = client.get("/api/v1/ai-usage/diagnostics?page=2&page_size=1")

    assert first_page_response.status_code == 200
    assert second_page_response.status_code == 200

    first_page = first_page_response.get_json()["data"]
    second_page = second_page_response.get_json()["data"]

    assert len(first_page["recent_calls"]) == 1
    assert len(second_page["recent_calls"]) == 1
    assert first_page["recent_calls_pagination"]["page"] == 1
    assert second_page["recent_calls_pagination"]["page"] == 2
    assert first_page["recent_calls_pagination"]["page_size"] == 1
    assert first_page["recent_calls_pagination"]["total_items"] >= 3
    assert first_page["recent_calls"][0]["id"] > second_page["recent_calls"][0]["id"]


@pytest.mark.functional
def test_admin_can_delete_image_library_item(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"d" * 24), "delete-me.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    delete_response = client.delete(
        f"/api/v1/image-library/images/{image_id}",
        headers=_csrf_headers(),
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["deleted"] is True

    list_response = client.get("/api/v1/image-library/images")
    assert list_response.status_code == 200
    ids = [item["id"] for item in list_response.get_json()["data"]]
    assert image_id not in ids


@pytest.mark.functional
def test_borrower_can_delete_unassigned_image_but_not_assigned_image(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["borrower_user_id"])

    unassigned_upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"u" * 24), "borrower-unassigned.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert unassigned_upload_response.status_code == 201
    unassigned_image_id = int(unassigned_upload_response.get_json()["data"]["created"][0]["id"])

    assigned_upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"a" * 24), "borrower-assigned.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert assigned_upload_response.status_code == 201
    assigned_image_id = int(assigned_upload_response.get_json()["data"]["created"][0]["id"])

    delete_unassigned_response = client.delete(
        f"/api/v1/image-library/images/{unassigned_image_id}",
        headers=_csrf_headers(),
    )
    assert delete_unassigned_response.status_code == 200
    assert delete_unassigned_response.get_json()["data"]["deleted"] is True

    delete_assigned_response = client.delete(
        f"/api/v1/image-library/images/{assigned_image_id}",
        headers=_csrf_headers(),
    )
    assert delete_assigned_response.status_code == 403


@pytest.mark.functional
def test_admin_can_bulk_upload_images_with_optional_jigsaw_association(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 20), "associated.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    created = response.get_json()["data"]["created"]
    assert len(created) == 1
    assert created[0]["jigsaw_id"] == seeded_image_library_data["jigsaw_id"]


@pytest.mark.functional
def test_bulk_upload_can_extract_images_from_zip_and_skip_non_images(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    archive = _make_zip_file(
        [
            ("photos/box-front.png", b"\x89PNG\r\n\x1a\n" + b"p" * 32),
            ("notes/readme.txt", b"not-an-image"),
            ("completed.jpg", b"\xff\xd8\xff" + b"j" * 64),
        ]
    )

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (archive, "bundle.zip", "application/zip"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["created_count"] == 2
    assert payload["skipped_count"] == 1
    assert any(item["issue"] == "not an image file" for item in payload["skipped"])


@pytest.mark.functional
def test_bulk_upload_skips_duplicate_image_content(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    image_bytes = b"\x89PNG\r\n\x1a\n" + (b"dup" * 64)

    first_upload = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(image_bytes), "existing.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert first_upload.status_code == 201
    assert first_upload.get_json()["data"]["created_count"] == 1

    second_upload = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (BytesIO(image_bytes), "duplicate-new-name.png", "image/png"),
                (BytesIO(image_bytes), "duplicate-again.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert second_upload.status_code == 201
    payload = second_upload.get_json()["data"]
    assert payload["created_count"] == 0
    assert payload["skipped_count"] == 2
    assert all("duplicate image content" in item["issue"] for item in payload["skipped"])
    reasons = [item.get("reason") for item in payload["skipped"] if item.get("reason")]
    assert any(
        reason == 'Image already exists, attached to jigsaw "Library Puzzle".'
        for reason in reasons
    )
    assert all(reason and "Image already exists" in reason for reason in reasons)


@pytest.mark.functional
def test_bulk_upload_rejects_missing_files(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["details"][0]["field"] == "files"


@pytest.mark.functional
def test_bulk_upload_rejects_unknown_jigsaw_reference(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": "999999",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n"), "orphan.png", "image/png")],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 404


@pytest.mark.functional
def test_unassigned_image_content_is_accessible_to_authenticated_users(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"c" * 24), "content.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image = upload_response.get_json()["data"]["created"][0]

    _set_user_session(client, seeded_image_library_data["borrower_user_id"])
    content_response = client.get(image["content_url"])
    thumbnail_response = client.get(image["thumbnail_url"])
    preview_response = client.get(image["preview_url"])

    assert content_response.status_code == 200
    assert content_response.mimetype == "image/png"
    assert thumbnail_response.status_code == 200
    assert preview_response.status_code == 200


@pytest.mark.functional
def test_image_content_variant_query_is_validated(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"v" * 24), "variant.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image = upload_response.get_json()["data"]["created"][0]

    invalid_variant_response = client.get(f"{image['content_url']}?variant=unsupported")
    assert invalid_variant_response.status_code == 422
    payload = invalid_variant_response.get_json()
    assert payload["error"]["details"][0]["field"] == "variant"


@pytest.mark.functional
def test_image_library_list_validates_limit(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.get("/api/v1/image-library/images?limit=1000")

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["details"][0]["field"] == "limit"


@pytest.mark.functional
def test_image_library_list_supports_page_and_page_size(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"m" * 24), "page-one.png", "image/png"),
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"n" * 24), "page-two.png", "image/png"),
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"o" * 24), "page-three.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    response = client.get("/api/v1/image-library/images?page=2&page_size=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) == 1
    assert payload["meta"]["page"] == 2
    assert payload["meta"]["page_size"] == 1
    assert payload["meta"]["total_items"] >= 3
    assert payload["meta"]["total_pages"] >= 3


@pytest.mark.functional
def test_admin_can_assign_unassigned_image_to_jigsaw(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"d" * 24), "assign-me.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    assign_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": seeded_image_library_data["jigsaw_id"]},
    )

    assert assign_response.status_code == 200
    assigned = assign_response.get_json()["data"]
    assert assigned["jigsaw_id"] == seeded_image_library_data["jigsaw_id"]


@pytest.mark.functional
def test_admin_can_unassign_assigned_image(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"u" * 24), "assigned.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    unassign_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": None},
    )

    assert unassign_response.status_code == 200
    unassigned = unassign_response.get_json()["data"]
    assert unassigned["jigsaw_id"] is None


@pytest.mark.functional
def test_assign_image_rejects_reassignment_to_different_jigsaw(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    with app.app_context():
        db_session = get_session()
        other = Jigsaw(title="Other", piece_count=500, status=JigsawStatus.AVAILABLE)
        db_session.add(other)
        db_session.flush()
        other_id = other.id
        db_session.commit()

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"e" * 24), "already-assigned.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    assign_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": other_id},
    )

    assert assign_response.status_code == 409


@pytest.mark.functional
def test_assign_image_validates_payload(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.patch(
        "/api/v1/image-library/images/1/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": "abc"},
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["details"][0]["field"] == "jigsaw_id"


@pytest.mark.functional
def test_assign_image_requires_jigsaw_id_field(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.patch(
        "/api/v1/image-library/images/1/assign",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["details"][0]["field"] == "jigsaw_id"


@pytest.mark.functional
def test_admin_can_set_image_tag_before_assignment(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"g" * 24), "tag-me.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    tag_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/tag",
        headers=_csrf_headers(),
        json={"tag": "Completed"},
    )

    assert tag_response.status_code == 200
    assert tag_response.get_json()["data"]["tag"] == "Completed"


@pytest.mark.functional
def test_image_tag_update_normalizes_known_tags_to_camel_case(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"h" * 24), "normalize-tag.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    tag_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/tag",
        headers=_csrf_headers(),
        json={"tag": "box-back"},
    )

    assert tag_response.status_code == 200
    assert tag_response.get_json()["data"]["tag"] == "Box back"


@pytest.mark.functional
def test_image_library_upload_normalizes_known_tags_to_camel_case(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "in-progress",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"i" * 24), "normalize-upload-tag.png", "image/png")],
        },
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 201
    created_image = upload_response.get_json()["data"]["created"][0]
    assert created_image["tag"] == "In progress"


@pytest.mark.functional
def test_reference_tag_normalizes_on_upload_and_patch(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "reference-image",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"r" * 24), "reference-upload.png", "image/png")],
        },
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 201
    created_image = upload_response.get_json()["data"]["created"][0]
    assert created_image["tag"] == "Reference"

    image_id = created_image["id"]
    patch_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/tag",
        headers=_csrf_headers(),
        json={"tag": "reference"},
    )
    assert patch_response.status_code == 200
    assert patch_response.get_json()["data"]["tag"] == "Reference"


@pytest.mark.functional
def test_completed_tag_on_assigned_image_creates_diary_entry(client, seeded_image_library_data, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    captured_at = datetime(2024, 4, 5, 12, 30, 0, tzinfo=timezone.utc)

    def fake_capture(_image_data):
        return captured_at, "exif_datetime_original", "2024:04:05 12:30:00"

    monkeypatch.setattr("app.api.v1.routes._extract_image_captured_at", fake_capture)

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 24), "done.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    tag_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/tag",
        headers=_csrf_headers(),
        json={"tag": "Completed"},
    )
    assert tag_response.status_code == 200

    diary_response = client.get(f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/diary-entries")
    assert diary_response.status_code == 200
    entries = diary_response.get_json()["data"]
    assert len(entries) == 1
    assert entries[0]["source_image_id"] == image_id
    assert entries[0]["completed_at"].startswith("2024-04-05T12:30:00")


@pytest.mark.functional
def test_assigning_completed_image_creates_diary_entry(client, seeded_image_library_data, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    captured_at = datetime(2022, 9, 10, 8, 45, 0, tzinfo=timezone.utc)

    def fake_capture(_image_data):
        return captured_at, "exif_datetime_original", "2022:09:10 08:45:00"

    monkeypatch.setattr("app.api.v1.routes._extract_image_captured_at", fake_capture)

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "Completed",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"y" * 24), "completed-first.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    assign_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": seeded_image_library_data["jigsaw_id"]},
    )
    assert assign_response.status_code == 200

    diary_response = client.get(f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/diary-entries")
    assert diary_response.status_code == 200
    entries = diary_response.get_json()["data"]
    assert len(entries) == 1
    assert entries[0]["source_image_id"] == image_id
    assert entries[0]["completed_at"].startswith("2022-09-10T08:45:00")


@pytest.mark.functional
def test_assigning_completed_image_with_naive_capture_time_does_not_crash(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "Completed",
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"m" * 24), "completed-naive.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    with app.app_context():
        db_session = get_session()
        image = db_session.get(JigsawImage, image_id)
        jigsaw = db_session.get(Jigsaw, seeded_image_library_data["jigsaw_id"])
        assert image is not None
        assert jigsaw is not None

        image.captured_at = datetime(2023, 1, 2, 3, 4, 5)
        jigsaw.last_completed_at = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        db_session.commit()

    assign_response = client.patch(
        f"/api/v1/image-library/images/{image_id}/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": seeded_image_library_data["jigsaw_id"]},
    )
    assert assign_response.status_code == 200

    diary_response = client.get(f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/diary-entries")
    assert diary_response.status_code == 200
    entries = diary_response.get_json()["data"]
    assert len(entries) == 1
    assert entries[0]["source_image_id"] == image_id


@pytest.mark.functional
def test_duplicate_upload_backfills_capture_metadata_when_missing(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    image_bytes = b"\x89PNG\r\n\x1a\n" + b"z" * 24

    def no_capture(_image_data):
        return None, None, None

    monkeypatch.setattr("app.api.v1.routes._extract_image_captured_at", no_capture)

    first_upload = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(image_bytes), "no-meta.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert first_upload.status_code == 201
    image_id = first_upload.get_json()["data"]["created"][0]["id"]

    captured_at = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    def with_capture(_image_data):
        return captured_at, "exif_datetime_original", "2020:01:02 03:04:05"

    monkeypatch.setattr("app.api.v1.routes._extract_image_captured_at", with_capture)

    second_upload = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(image_bytes), "with-meta.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert second_upload.status_code == 201
    payload = second_upload.get_json()["data"]
    assert payload["created_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["metadata_backfilled_count"] == 1
    assert payload["skipped"][0]["metadata_backfilled"] is True

    with app.app_context():
        db_session = get_session()
        image = db_session.get(JigsawImage, image_id)
        assert image is not None
        stored_captured_at = image.captured_at
        if stored_captured_at is not None and stored_captured_at.tzinfo is None:
            stored_captured_at = stored_captured_at.replace(tzinfo=timezone.utc)
        assert stored_captured_at == captured_at


@pytest.mark.functional
def test_admin_can_overwrite_image_content(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    original_bytes = b"\x89PNG\r\n\x1a\n" + b"h" * 24

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(original_bytes), "before.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    created = upload_response.get_json()["data"]["created"][0]
    image_id = created["id"]

    overwrite_response = client.put(
        f"/api/v1/image-library/images/{image_id}/content",
        headers=_csrf_headers(),
        data={
            "image": (BytesIO(b"\x89PNG\r\n\x1a\n" + b"i" * 96), "after.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert overwrite_response.status_code == 200
    updated = overwrite_response.get_json()["data"]
    assert updated["filename"] == "after.png"

    content_response = client.get(updated["content_url"])
    assert content_response.status_code == 200
    assert content_response.data == b"\x89PNG\r\n\x1a\n" + b"i" * 96

    duplicate_original_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(original_bytes), "before-again-different-name.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert duplicate_original_response.status_code == 201
    payload = duplicate_original_response.get_json()["data"]
    assert payload["created_count"] == 0
    assert payload["skipped_count"] == 1
    assert "duplicate image content" in payload["skipped"][0]["issue"]


@pytest.mark.functional
def test_admin_can_create_jigsaw_from_unassigned_image_with_ai_inference(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"z" * 24), "create-me.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0
    app.config["AI_INPUT_COST_PER_1K_TOKENS_USD"] = 0.001
    app.config["AI_OUTPUT_COST_PER_1K_TOKENS_USD"] = 0.002

    def fake_inference(_image):
        return {
            "metadata": {
                "title": "Inferred Puzzle",
                "series_name": "My Haven Series",
                "series_number": "10",
                "publisher": "Ravensburger",
                "artist": "Sample Artist",
                "piece_count": 1000,
                "tags": ["landscape", "sunset"],
                "dimensions_cm": "70 x 50 cm",
                "description": "Inferred from box image",
            },
            "provider_response": {
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"Inferred Puzzle","series_name":"My Haven Series"}'
                        }
                    }
                ]
            },
            "provider_response_text": '{"choices":[{"message":{"content":"{\\"title\\":\\"Inferred Puzzle\\"}"}}]}',
            "prompt_tokens": 500,
            "completion_tokens": 120,
            "total_tokens": 620,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.07,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", fake_inference)

    create_response = client.post(
        f"/api/v1/image-library/images/{image_id}/create-jigsaw",
        headers=_csrf_headers(),
        json={},
    )

    assert create_response.status_code == 201
    payload = create_response.get_json()["data"]
    assert payload["jigsaw"]["title"] == "Inferred Puzzle"
    assert payload["jigsaw"]["series_name"] == "My Haven Series"
    assert payload["jigsaw"]["series_number"] == "10"
    assert payload["jigsaw"]["manufacturer"] == "Ravensburger"
    assert payload["image"]["jigsaw_id"] == payload["jigsaw"]["id"]
    assert payload["image"]["tag"] == "Box"
    assert payload["ai"]["prompt_tokens"] == 500

    with app.app_context():
        db_session = get_session()
        usage_rows = db_session.query(AiUsageEvent).filter_by(operation="image_to_jigsaw", status="success").all()
        assert len(usage_rows) == 1
        payload = json.loads(usage_rows[0].payload_json)
        assert isinstance(payload.get("provider_response"), dict)
        assert "provider_response_text" in payload


@pytest.mark.functional
def test_create_jigsaw_from_image_tolerates_messy_ai_payload_types(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"m" * 24), "messy-payload.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0

    def fake_inference(_image):
        return {
            "metadata": {
                "title": "Messy Inference",
                "series_name": 123,
                "series_number": True,
                "manufacturer": "Ravensburger",
                "artist": ["not", "a", "string"],
                "piece_count": "1,000 pieces",
                "tags": ["landscape", 42, None, {"bad": "value"}],
                "dimensions_cm": "70 x 50 cm",
                "description": "Text extracted from the box",
            },
            "prompt_tokens": 123,
            "completion_tokens": 45,
            "total_tokens": 168,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.03,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", fake_inference)

    create_response = client.post(
        f"/api/v1/image-library/images/{image_id}/create-jigsaw",
        headers=_csrf_headers(),
        json={},
    )

    assert create_response.status_code == 201
    payload = create_response.get_json()["data"]
    assert payload["jigsaw"]["title"] == "Messy Inference"
    assert payload["jigsaw"]["piece_count"] == 1000
    assert payload["jigsaw"]["manufacturer"] == "Ravensburger"
    assert payload["jigsaw"]["series_name"] == "123"
    assert payload["jigsaw"]["series_number"] is None
    assert payload["jigsaw"]["artist"] is None
    assert payload["jigsaw"]["tags"] == "landscape, 42"


@pytest.mark.functional
def test_create_jigsaw_from_image_invalid_payload_stores_provider_response(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"r" * 24), "invalid-shape.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0

    def fake_inference(_image):
        return {
            "metadata": "not-a-dict",
            "provider_response": {"choices": [{"message": {"content": "not-a-dict"}}]},
            "provider_response_text": '{"choices":[{"message":{"content":"not-a-dict"}}]}',
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "total_tokens": 8,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.0,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", fake_inference)

    response = client.post(
        f"/api/v1/image-library/images/{image_id}/create-jigsaw",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 502

    diagnostics_response = client.get("/api/v1/ai-usage/diagnostics?limit=10")
    assert diagnostics_response.status_code == 200
    recent_calls = diagnostics_response.get_json()["data"]["recent_calls"]
    error_row = next(row for row in recent_calls if row["error_code"] == "invalid_ai_payload")
    assert isinstance(error_row["payload"], dict)
    assert error_row["payload"]["provider_response"] == {"choices": [{"message": {"content": "not-a-dict"}}]}


@pytest.mark.functional
def test_create_jigsaw_from_image_respects_daily_budget(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"k" * 24), "budget.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 0.0

    def should_not_be_called(_image):  # pragma: no cover
        raise AssertionError("AI inference should not run when budget is exhausted")

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", should_not_be_called)

    response = client.post(
        f"/api/v1/image-library/images/{image_id}/create-jigsaw",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["message"] == "Daily AI budget has been reached for create-from-image."

    with app.app_context():
        db_session = get_session()
        blocked_rows = db_session.query(AiUsageEvent).filter_by(operation="image_to_jigsaw", status="blocked").all()
        assert len(blocked_rows) == 1


@pytest.mark.functional
def test_create_jigsaw_from_image_rejects_already_assigned_images(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"m" * 24), "assigned.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["AI_ENABLED"] = True

    response = client.post(
        f"/api/v1/image-library/images/{image_id}/create-jigsaw",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 409


@pytest.mark.functional
def test_admin_can_enrich_jigsaw_from_assigned_images_non_destructive(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_box_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "tag": "Box",
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"f" * 32), "front.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_box_response.status_code == 201

    upload_completed_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "tag": "Completed",
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"b" * 32), "completed.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_completed_response.status_code == 201

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0

    observed = {"count": 0, "tags": []}

    def fake_inference(_images, _instruction_text):
        observed["count"] = len(_images)
        observed["tags"] = [image.tag for image in _images]
        return {
            "metadata": {
                "title": "Should Not Replace Existing Title",
                "series_name": "My Haven Series",
                "series_number": "10",
                "publisher": "Ravensburger",
                "artist": "Jane Doe",
                "piece_count": 1500,
                "tags": ["cozy", "kitchen"],
                "dimensions_cm": "70 x 50 cm",
                "description": "Details collected across front and back images",
            },
            "prompt_tokens": 610,
            "completion_tokens": 130,
            "total_tokens": 740,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.08,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_images", fake_inference)

    enrich_response = client.post(
        f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/enrich-from-images",
        headers=_csrf_headers(),
        json={},
    )
    assert enrich_response.status_code == 200
    payload = enrich_response.get_json()["data"]
    assert payload["jigsaw"]["title"] == "Library Puzzle"
    assert payload["jigsaw"]["series_name"] == "My Haven Series"
    assert payload["jigsaw"]["series_number"] == "10"
    assert payload["jigsaw"]["manufacturer"] == "Ravensburger"
    assert payload["jigsaw"]["artist"] == "Jane Doe"
    assert payload["jigsaw"]["piece_count"] == 1000
    assert "title" not in payload["applied_fields"]
    assert "piece_count" not in payload["applied_fields"]
    assert "series_name" in payload["applied_fields"]
    assert payload["ai"]["prompt_tokens"] == 610
    assert observed["count"] == 1
    assert observed["tags"] == ["Box"]


@pytest.mark.functional
def test_enrich_jigsaw_from_images_rejects_without_images(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])
    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"

    response = client.post(
        f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/enrich-from-images",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["message"] == "Jigsaw has no associated images to enrich from."


@pytest.mark.functional
def test_enrich_jigsaw_from_images_rejects_without_box_tagged_images(client, seeded_image_library_data, app):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "tag": "Completed",
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"c" * 32), "completed-only.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"

    response = client.post(
        f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/enrich-from-images",
        headers=_csrf_headers(),
        json={},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["message"] == "Jigsaw has no box-tagged images to enrich from."


@pytest.mark.functional
def test_admin_can_start_bulk_create_jigsaws_job(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "tag": "Box",
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"a" * 32), "bulk-create-one.png", "image/png"),
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"b" * 32), "bulk-create-two.png", "image/png"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    created_images = upload_response.get_json()["data"]["created"]
    image_ids = [item["id"] for item in created_images]

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0

    def fake_inference(image):
        return {
            "metadata": {
                "title": f"Bulk Inferred {image.id}",
                "series_name": None,
                "series_number": None,
                "publisher": "Ravensburger",
                "artist": None,
                "piece_count": 500,
                "tags": ["bulk", "import"],
                "dimensions_cm": None,
                "description": "Bulk create",
            },
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.01,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", fake_inference)

    start_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws",
        headers=_csrf_headers(),
        json={"image_ids": image_ids},
    )
    assert start_response.status_code == 202
    start_payload = start_response.get_json()["data"]["job"]
    assert start_payload["status"] == "completed"
    assert start_payload["total_items"] == 2
    assert start_payload["succeeded_items"] == 2
    assert start_payload["failed_items"] == 0

    job_id = start_payload["id"]
    status_response = client.get(f"/api/v1/image-library/bulk-create-jigsaws/{job_id}")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()["data"]["job"]
    assert status_payload["status"] == "completed"

    items_response = client.get(f"/api/v1/image-library/bulk-create-jigsaws/{job_id}/items?page=1&page_size=10")
    assert items_response.status_code == 200
    items_payload = items_response.get_json()
    assert items_payload["meta"]["total_items"] == 2
    assert len(items_payload["data"]) == 2
    assert all(item["status"] == "completed" for item in items_payload["data"])

    with app.app_context():
        db_session = get_session()
        images = db_session.query(JigsawImage).filter(JigsawImage.id.in_(image_ids)).all()
        assert len(images) == 2
        assert all(image.jigsaw_id is not None for image in images)
        assert all(image.tag == "Box" for image in images)


@pytest.mark.functional
def test_admin_can_start_bulk_create_for_all_unassigned_box_images(client, seeded_image_library_data, app, monkeypatch):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [
                (BytesIO(b"\x89PNG\r\n\x1a\n" + b"d" * 32), "all-box-1.png", "image/png"),
            ],
            "tag": "Box",
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    side_upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"e" * 32), "all-box-side.png", "image/png")],
            "tag": "Box side",
        },
        content_type="multipart/form-data",
    )
    assert side_upload_response.status_code == 201

    assigned_upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "jigsaw_id": str(seeded_image_library_data["jigsaw_id"]),
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"f" * 32), "assigned-box.png", "image/png")],
            "tag": "Box",
        },
        content_type="multipart/form-data",
    )
    assert assigned_upload_response.status_code == 201

    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"
    app.config["AI_DAILY_BUDGET_USD"] = 10.0

    def fake_inference(image):
        return {
            "metadata": {
                "title": f"All Box Inferred {image.id}",
                "series_name": None,
                "series_number": None,
                "publisher": "Ravensburger",
                "artist": None,
                "piece_count": 300,
                "tags": ["bulk"],
                "dimensions_cm": None,
                "description": "Bulk create",
            },
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "provider_cost_usd": None,
            "computed_cost_usd": None,
            "final_cost_usd": 0.01,
            "model": "mock-vision",
            "endpoint_url": "https://example.invalid/v1/chat/completions",
        }

    monkeypatch.setattr("app.api.v1.routes._infer_jigsaw_metadata_from_image", fake_inference)

    start_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws/unassigned-box",
        headers=_csrf_headers(),
        json={},
    )
    assert start_response.status_code == 202
    job = start_response.get_json()["data"]["job"]
    assert job["status"] == "completed"
    assert job["total_items"] == 1
    assert job["succeeded_items"] == 1


@pytest.mark.functional
def test_bulk_create_jigsaws_job_tracks_failed_items(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"c" * 32), "bulk-create-fail.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    start_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws",
        headers=_csrf_headers(),
        json={"image_ids": [image_id]},
    )
    assert start_response.status_code == 202
    job = start_response.get_json()["data"]["job"]
    assert job["status"] == "failed"
    assert job["failed_items"] == 1

    items_response = client.get(f"/api/v1/image-library/bulk-create-jigsaws/{job['id']}/items")
    assert items_response.status_code == 200
    items = items_response.get_json()["data"]
    assert len(items) == 1
    assert items[0]["status"] == "failed"
    assert items[0]["error_code"] == "conflict"


@pytest.mark.functional
def test_bulk_create_job_non_inline_kickstarts_thread_on_create_and_status_poll(
    client, seeded_image_library_data, app, monkeypatch
):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    upload_response = client.post(
        "/api/v1/image-library/uploads",
        headers=_csrf_headers(),
        data={
            "files": [(BytesIO(b"\x89PNG\r\n\x1a\n" + b"k" * 32), "bulk-kickstart.png", "image/png")],
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.get_json()["data"]["created"][0]["id"]

    app.config["BULK_AI_CREATE_INLINE"] = False
    launched_job_ids = []

    def fake_start_job_thread(flask_app, job_id):
        assert flask_app is app
        launched_job_ids.append(int(job_id))

    monkeypatch.setattr("app.api.v1.routes._start_bulk_ai_create_job_thread", fake_start_job_thread)

    start_response = client.post(
        "/api/v1/image-library/bulk-create-jigsaws",
        headers=_csrf_headers(),
        json={"image_ids": [image_id]},
    )
    assert start_response.status_code == 202
    job = start_response.get_json()["data"]["job"]
    assert job["status"] == "queued"
    assert launched_job_ids == [job["id"]]

    launched_job_ids.clear()
    status_response = client.get(f"/api/v1/image-library/bulk-create-jigsaws/{job['id']}")
    assert status_response.status_code == 200
    assert launched_job_ids == [job["id"]]
    status_job = status_response.get_json()["data"]["job"]
    assert status_job["status"] == "queued"
