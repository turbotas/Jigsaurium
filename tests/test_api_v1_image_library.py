from io import BytesIO
import zipfile

import pytest

from app.db import get_session
from app.models import AiUsageEvent, Jigsaw, Role, User, UserRole
from app.models.jigsaw import JigsawStatus


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


@pytest.mark.functional
@pytest.mark.parametrize(
    ("method", "path", "content_type", "json_payload"),
    [
        ("GET", "/api/v1/image-library/images", None, None),
        ("POST", "/api/v1/image-library/uploads", "multipart/form-data", None),
        ("PATCH", "/api/v1/image-library/images/1/assign", None, {"jigsaw_id": 1}),
        ("GET", "/api/v1/images/1/content", None, None),
    ],
)
def test_image_library_endpoints_require_authentication(
    client, seeded_image_library_data, method, path, content_type, json_payload
):
    if method == "POST":
        response = client.open(
            path,
            method=method,
            data={"files": (BytesIO(b"\x89PNG\r\n\x1a\n"), "one.png", "image/png")},
            content_type=content_type,
        )
    elif method == "PATCH":
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

    assign_response = client.patch(
        "/api/v1/image-library/images/1/assign",
        headers=_csrf_headers(),
        json={"jigsaw_id": seeded_image_library_data["jigsaw_id"]},
    )
    assert assign_response.status_code == 403


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

    assert content_response.status_code == 200
    assert content_response.mimetype == "image/png"


@pytest.mark.functional
def test_image_library_list_validates_limit(client, seeded_image_library_data):
    _set_user_session(client, seeded_image_library_data["admin_user_id"])

    response = client.get("/api/v1/image-library/images?limit=1000")

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["details"][0]["field"] == "limit"


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
                "publisher": "Ravensburger",
                "artist": "Sample Artist",
                "piece_count": 1000,
                "tags": ["landscape", "sunset"],
                "dimensions_cm": "70 x 50 cm",
                "description": "Inferred from box image",
            },
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
    assert payload["jigsaw"]["manufacturer"] == "Ravensburger"
    assert payload["image"]["jigsaw_id"] == payload["jigsaw"]["id"]
    assert payload["image"]["tag"] == "Box"
    assert payload["ai"]["prompt_tokens"] == 500

    with app.app_context():
        db_session = get_session()
        usage_rows = db_session.query(AiUsageEvent).filter_by(operation="image_to_jigsaw", status="success").all()
        assert len(usage_rows) == 1


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
