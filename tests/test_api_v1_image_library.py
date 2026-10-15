from datetime import datetime, timezone
from io import BytesIO
import zipfile

import pytest

from app.db import get_session
from app.models import AiUsageEvent, Jigsaw, JigsawImage, Role, User, UserRole
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
        ("PATCH", "/api/v1/image-library/images/1/tag", None, {"tag": "Box"}),
        ("DELETE", "/api/v1/image-library/images/1", None, None),
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
    assert delete_response.status_code == 403

    enrich_response = client.post(
        f"/api/v1/jigsaws/{seeded_image_library_data['jigsaw_id']}/enrich-from-images",
        headers=_csrf_headers(),
        json={},
    )
    assert enrich_response.status_code == 403


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
