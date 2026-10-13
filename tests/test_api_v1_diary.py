from datetime import datetime, timezone

import pytest

from app.db import get_session
from app.models import AuditEvent, Jigsaw, Role, User, UserRole
from app.models.jigsaw import JigsawStatus


@pytest.fixture()
def seeded_diary_data(app):
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

        available_jigsaw = Jigsaw(
            title="Harbor Sunset",
            piece_count=1000,
            status=JigsawStatus.AVAILABLE,
        )
        retired_jigsaw = Jigsaw(
            title="Old Castle",
            piece_count=1500,
            status=JigsawStatus.RETIRED,
        )
        db_session.add_all([available_jigsaw, retired_jigsaw])
        db_session.flush()

        db_session.commit()

        seeded_ids = {
            "admin_user_id": admin_user.id,
            "borrower_user_id": borrower_user.id,
            "available_jigsaw_id": available_jigsaw.id,
            "retired_jigsaw_id": retired_jigsaw.id,
        }

    # Release the app context before yielding: keeping it pushed makes the
    # test client reuse it per request, leaking g-cached users across requests.
    db_session.remove()
    yield seeded_ids


def _set_user_session(client, user_id, csrf_token="test-csrf-token"):
    with client.session_transaction() as test_session:
        test_session["user_id"] = user_id
        test_session["csrf_token"] = csrf_token


def _csrf_headers(csrf_token="test-csrf-token"):
    return {"X-CSRF-Token": csrf_token}


def _parse_timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _create_entry(client, jigsaw_id, payload):
    return client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/diary-entries",
        json=payload,
        headers=_csrf_headers(),
    )


def _get_jigsaw(client, jigsaw_id):
    return client.get(f"/api/v1/jigsaws/{jigsaw_id}")


@pytest.mark.functional
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("GET", "/api/v1/jigsaws/1/diary-entries", None),
        ("POST", "/api/v1/jigsaws/1/diary-entries", {"notes": "No session"}),
        ("DELETE", "/api/v1/diary-entries/1", None),
    ],
)
def test_diary_endpoints_require_authentication(client, seeded_diary_data, method, path, json_payload):
    response = client.open(path, method=method, json=json_payload)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


@pytest.mark.functional
def test_diary_create_forbidden_for_borrower(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["borrower_user_id"])

    response = _create_entry(client, seeded_diary_data["available_jigsaw_id"], {"notes": "Nope"})

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_diary_delete_forbidden_for_borrower(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    created = _create_entry(client, seeded_diary_data["available_jigsaw_id"], {"notes": "Mine"})
    entry_id = created.get_json()["data"]["id"]

    _set_user_session(client, seeded_diary_data["borrower_user_id"])
    response = client.delete(f"/api/v1/diary-entries/{entry_id}", headers=_csrf_headers())

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_diary_list_allows_borrower_for_available_jigsaw(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["borrower_user_id"])

    response = client.get(f"/api/v1/jigsaws/{seeded_diary_data['available_jigsaw_id']}/diary-entries")

    assert response.status_code == 200
    assert response.get_json()["data"] == []


@pytest.mark.functional
def test_diary_list_hides_retired_jigsaw_from_borrower(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["borrower_user_id"])

    response = client.get(f"/api/v1/jigsaws/{seeded_diary_data['retired_jigsaw_id']}/diary-entries")

    assert response.status_code == 404


@pytest.mark.functional
def test_diary_list_missing_jigsaw_returns_not_found(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = client.get("/api/v1/jigsaws/99999/diary-entries")

    assert response.status_code == 404


@pytest.mark.functional
def test_diary_create_sets_fields_and_bumps_last_completed(client, seeded_diary_data, app):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    jigsaw_id = seeded_diary_data["available_jigsaw_id"]

    response = _create_entry(
        client,
        jigsaw_id,
        {
            "completed_at": "2026-10-01T18:30:00Z",
            "difficulty": 4,
            "notes": "Sky section was brutal.",
        },
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["jigsaw_id"] == jigsaw_id
    assert data["difficulty"] == 4
    assert data["notes"] == "Sky section was brutal."
    assert data["completed_at"].startswith("2026-10-01T18:30:00")
    assert data["created_at"]
    assert data["updated_at"]

    jigsaw_payload = _get_jigsaw(client, jigsaw_id).get_json()["data"]
    assert jigsaw_payload["last_completed_at"].startswith("2026-10-01T18:30:00")

    with app.app_context():
        db_session = get_session()
        event = db_session.query(AuditEvent).filter_by(action="jigsaw.diary_entry_created").one()
        assert event.entity_type == "jigsaw_diary_entry"
        assert event.entity_id == str(data["id"])
        assert event.actor_user_id == seeded_diary_data["admin_user_id"]


@pytest.mark.functional
def test_diary_create_with_empty_body_applies_defaults(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    jigsaw_id = seeded_diary_data["available_jigsaw_id"]

    response = _create_entry(client, jigsaw_id, {})

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["difficulty"] is None
    assert data["notes"] is None

    completed_at = datetime.fromisoformat(data["completed_at"])
    assert completed_at.tzinfo is not None
    assert (datetime.now(timezone.utc) - completed_at).total_seconds() < 60

    jigsaw_payload = _get_jigsaw(client, jigsaw_id).get_json()["data"]
    assert _parse_timestamp(jigsaw_payload["last_completed_at"]) == _parse_timestamp(data["completed_at"])


@pytest.mark.functional
def test_diary_create_does_not_move_last_completed_backwards(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    jigsaw_id = seeded_diary_data["available_jigsaw_id"]

    newer = _create_entry(client, jigsaw_id, {"completed_at": "2026-10-10T10:00:00Z"})
    assert newer.status_code == 201

    older = _create_entry(client, jigsaw_id, {"completed_at": "2026-09-01T10:00:00Z"})
    assert older.status_code == 201

    jigsaw_payload = _get_jigsaw(client, jigsaw_id).get_json()["data"]
    assert jigsaw_payload["last_completed_at"].startswith("2026-10-10T10:00:00")


@pytest.mark.functional
@pytest.mark.parametrize(
    "difficulty",
    [0, 6, -1, "abc", True, 3.5, {"value": 3}],
)
def test_diary_create_rejects_invalid_difficulty(client, seeded_diary_data, difficulty):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(client, seeded_diary_data["available_jigsaw_id"], {"difficulty": difficulty})

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert any(detail["field"] == "difficulty" for detail in payload["error"]["details"])


@pytest.mark.functional
def test_diary_create_accepts_string_difficulty(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(client, seeded_diary_data["available_jigsaw_id"], {"difficulty": "3"})

    assert response.status_code == 201
    assert response.get_json()["data"]["difficulty"] == 3


@pytest.mark.functional
def test_diary_create_rejects_overlong_notes(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(
        client,
        seeded_diary_data["available_jigsaw_id"],
        {"notes": "x" * 4001},
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert any(detail["field"] == "notes" for detail in payload["error"]["details"])


@pytest.mark.functional
def test_diary_create_rejects_control_characters_in_notes(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(
        client,
        seeded_diary_data["available_jigsaw_id"],
        {"notes": "bad\x07notes"},
    )

    assert response.status_code == 422


@pytest.mark.functional
def test_diary_create_rejects_invalid_completed_at(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(
        client,
        seeded_diary_data["available_jigsaw_id"],
        {"completed_at": "not-a-date"},
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert any(detail["field"] == "completed_at" for detail in payload["error"]["details"])


@pytest.mark.functional
def test_diary_create_missing_jigsaw_returns_not_found(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = _create_entry(client, 99999, {"notes": "Ghost"})

    assert response.status_code == 404


@pytest.mark.functional
def test_diary_list_orders_newest_completion_first(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    jigsaw_id = seeded_diary_data["available_jigsaw_id"]

    _create_entry(client, jigsaw_id, {"completed_at": "2026-08-01T10:00:00Z", "notes": "first"})
    _create_entry(client, jigsaw_id, {"completed_at": "2026-10-01T10:00:00Z", "notes": "third"})
    _create_entry(client, jigsaw_id, {"completed_at": "2026-09-01T10:00:00Z", "notes": "second"})

    response = client.get(f"/api/v1/jigsaws/{jigsaw_id}/diary-entries")

    assert response.status_code == 200
    notes = [entry["notes"] for entry in response.get_json()["data"]]
    assert notes == ["third", "second", "first"]


@pytest.mark.functional
def test_diary_delete_recomputes_last_completed(client, seeded_diary_data, app):
    _set_user_session(client, seeded_diary_data["admin_user_id"])
    jigsaw_id = seeded_diary_data["available_jigsaw_id"]

    older = _create_entry(client, jigsaw_id, {"completed_at": "2026-08-01T10:00:00Z"}).get_json()["data"]
    newer = _create_entry(client, jigsaw_id, {"completed_at": "2026-10-01T10:00:00Z"}).get_json()["data"]

    response = client.delete(f"/api/v1/diary-entries/{newer['id']}", headers=_csrf_headers())
    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == newer["id"]

    jigsaw_payload = _get_jigsaw(client, jigsaw_id).get_json()["data"]
    assert jigsaw_payload["last_completed_at"].startswith("2026-08-01T10:00:00")

    response = client.delete(f"/api/v1/diary-entries/{older['id']}", headers=_csrf_headers())
    assert response.status_code == 200

    jigsaw_payload = _get_jigsaw(client, jigsaw_id).get_json()["data"]
    assert jigsaw_payload["last_completed_at"] is None

    with app.app_context():
        db_session = get_session()
        events = db_session.query(AuditEvent).filter_by(action="jigsaw.diary_entry_deleted").count()
        assert events == 2


@pytest.mark.functional
def test_diary_delete_missing_entry_returns_not_found(client, seeded_diary_data):
    _set_user_session(client, seeded_diary_data["admin_user_id"])

    response = client.delete("/api/v1/diary-entries/99999", headers=_csrf_headers())

    assert response.status_code == 404
