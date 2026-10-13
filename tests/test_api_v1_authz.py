from datetime import datetime
from io import BytesIO

import pytest

from app.db import get_session
from app.models import AuditEvent, Jigsaw, Loan, Role, User, UserRole
from app.models.jigsaw import JigsawStatus
from app.models.loan import LoanStatus


@pytest.fixture()
def seeded_identity_data(app):
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
            condition="good",
            status=JigsawStatus.AVAILABLE,
            tags="coast,orange",
        )
        retired_jigsaw = Jigsaw(
            title="Old Castle",
            piece_count=1500,
            condition="fair",
            status=JigsawStatus.RETIRED,
            tags="history,stone",
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


def _count_audit_events(app):
    with app.app_context():
        db_session = get_session()
        return db_session.query(AuditEvent).count()


def _assert_authentication_required(response):
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["code"] == "authentication_required"
    assert payload["meta"]["request_id"].startswith("req_")


@pytest.mark.functional
def test_api_users_requires_authentication(client, seeded_identity_data):
    response = client.get("/api/v1/users")

    _assert_authentication_required(response)


@pytest.mark.functional
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("GET", "/api/v1/roles", None),
        ("GET", "/api/v1/jigsaws", None),
        ("GET", "/api/v1/loans", None),
        ("GET", "/api/v1/jigsaws/1/images", None),
        ("GET", "/api/v1/jigsaws/1", None),
        ("PATCH", "/api/v1/auth/me", {"display_name": "No Session"}),
        (
            "POST",
            "/api/v1/users",
            {
                "email": "someone@example.com",
                "password": "SomeonePass123!",
                "display_name": "Someone",
                "roles": ["borrower"],
            },
        ),
        ("PATCH", "/api/v1/users/1", {"display_name": "Updated"}),
        (
            "POST",
            "/api/v1/jigsaws",
            {"title": "Locked", "piece_count": 200, "status": "available"},
        ),
        ("POST", "/api/v1/loans", {"borrower_user_id": 1, "jigsaw_id": 1}),
        ("POST", "/api/v1/loans/1/return", {}),
        ("PATCH", "/api/v1/jigsaws/1", {"title": "Updated title"}),
        ("DELETE", "/api/v1/jigsaws/1", None),
        ("DELETE", "/api/v1/jigsaws/1/permanent", None),
        ("POST", "/api/v1/jigsaws/1/enrich-from-images", {}),
    ],
)
def test_protected_endpoints_require_authentication(client, seeded_identity_data, method, path, json_payload):
    response = client.open(path=path, method=method, json=json_payload)

    _assert_authentication_required(response)


@pytest.mark.functional
def test_api_users_forbidden_for_borrower_role(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get("/api/v1/users")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_api_users_returns_data_for_administrator(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.get("/api/v1/users")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) == 2
    assert payload["data"][0]["email"] == "admin@example.com"
    assert payload["data"][0]["roles"] == ["administrator"]
    assert payload["meta"]["request_id"].startswith("req_")


@pytest.mark.functional
def test_api_jigsaws_hides_retired_for_non_admin(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get("/api/v1/jigsaws")

    assert response.status_code == 200
    payload = response.get_json()
    titles = [entry["title"] for entry in payload["data"]]
    assert "Harbor Sunset" in titles
    assert "Old Castle" not in titles


@pytest.mark.functional
def test_api_jigsaws_includes_retired_for_administrator(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.get("/api/v1/jigsaws")

    assert response.status_code == 200
    payload = response.get_json()
    titles = [entry["title"] for entry in payload["data"]]
    assert "Harbor Sunset" in titles
    assert "Old Castle" in titles


@pytest.mark.functional
def test_api_roles_returns_seeded_roles_for_administrator(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.get("/api/v1/roles")

    assert response.status_code == 200
    payload = response.get_json()
    role_names = [entry["name"] for entry in payload["data"]]
    assert role_names == ["administrator", "borrower"]


@pytest.mark.functional
def test_api_create_user_creates_roles_and_audit_event(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    before_count = _count_audit_events(app)

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "new.user@example.com",
            "password": "NewUserPass123!",
            "display_name": "New User",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["data"]["email"] == "new.user@example.com"
    assert payload["data"]["roles"] == ["borrower"]
    assert _count_audit_events(app) == before_count + 1


@pytest.mark.functional
def test_api_create_user_accepts_multiple_roles(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "dual.role@example.com",
            "password": "DualRolePass123!",
            "display_name": "Dual Role",
            "is_active": True,
            "roles": ["administrator", "borrower"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["data"]["email"] == "dual.role@example.com"
    assert payload["data"]["roles"] == ["administrator", "borrower"]


@pytest.mark.functional
def test_api_update_user_updates_roles_and_active_flag(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    before_count = _count_audit_events(app)

    with app.app_context():
        db_session = get_session()
        borrower_user = db_session.query(User).filter_by(email="borrower@example.com").one()
        borrower_user_id = borrower_user.id

    response = client.patch(
        f"/api/v1/users/{borrower_user_id}",
        headers=_csrf_headers(),
        json={"is_active": False, "roles": ["administrator", "borrower"]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["is_active"] is False
    assert payload["data"]["roles"] == ["administrator", "borrower"]
    assert _count_audit_events(app) == before_count + 1


@pytest.mark.functional
def test_admin_can_edit_existing_user_and_reset_password(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    with app.app_context():
        db_session = get_session()
        borrower_user = db_session.query(User).filter_by(email="borrower@example.com").one()
        borrower_user_id = borrower_user.id

    update_response = client.patch(
        f"/api/v1/users/{borrower_user_id}",
        headers=_csrf_headers(),
        json={
            "display_name": "Borrower Edited",
            "password": "BorrowerPassword789!",
            "roles": ["borrower"],
            "is_active": True,
        },
    )

    assert update_response.status_code == 200
    updated_payload = update_response.get_json()
    assert updated_payload["data"]["display_name"] == "Borrower Edited"

    admin_logout_response = client.post("/api/v1/auth/logout", headers=_csrf_headers())
    assert admin_logout_response.status_code == 200

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword789!"},
    )
    assert new_login_response.status_code == 200


@pytest.mark.functional
def test_api_jigsaw_crud_and_retire_flow_records_audit(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    before_count = _count_audit_events(app)

    create_response = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={
            "title": "Mountain Lake",
            "piece_count": 750,
            "condition": "new",
            "status": "available",
            "tags": "water,mountains",
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()["data"]

    patch_response = client.patch(
        f"/api/v1/jigsaws/{created['id']}",
        headers=_csrf_headers(),
        json={"status": "maintenance", "condition": "damaged"},
    )
    assert patch_response.status_code == 200
    assert patch_response.get_json()["data"]["status"] == "maintenance"

    delete_response = client.delete(f"/api/v1/jigsaws/{created['id']}", headers=_csrf_headers())
    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["status"] == "retired"

    assert _count_audit_events(app) == before_count + 3


@pytest.mark.functional
def test_api_loans_forbidden_for_borrower_role(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get("/api/v1/loans")

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_admin_can_create_loan_sets_due_date_and_updates_jigsaw(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    before_count = _count_audit_events(app)

    response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["borrower_user_id"] == seeded_identity_data["borrower_user_id"]
    assert payload["jigsaw_id"] == seeded_identity_data["available_jigsaw_id"]
    assert payload["status"] == "active"

    checked_out_at = payload["checked_out_at"]
    due_at = payload["due_at"]
    assert checked_out_at is not None
    assert due_at is not None

    checked_out_timestamp = checked_out_at.replace("Z", "+00:00")
    due_timestamp = due_at.replace("Z", "+00:00")
    checked_out_dt = datetime.fromisoformat(checked_out_timestamp)
    due_dt = datetime.fromisoformat(due_timestamp)
    assert (due_dt - checked_out_dt).days == 28

    with app.app_context():
        db_session = get_session()
        loan = db_session.get(Loan, payload["id"])
        assert loan is not None
        assert loan.status == LoanStatus.ACTIVE

        jigsaw = db_session.get(Jigsaw, seeded_identity_data["available_jigsaw_id"])
        assert jigsaw.status == JigsawStatus.ON_LOAN

    assert _count_audit_events(app) == before_count + 1


@pytest.mark.functional
def test_admin_user_can_be_loan_borrower(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["admin_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["borrower_user_id"] == seeded_identity_data["admin_user_id"]


@pytest.mark.functional
def test_create_loan_rejects_non_available_jigsaw(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["retired_jigsaw_id"],
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"


@pytest.mark.functional
def test_create_loan_rejects_jigsaw_with_existing_active_loan(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    create_first = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )
    assert create_first.status_code == 201

    create_second = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )

    assert create_second.status_code == 409
    assert create_second.get_json()["error"]["code"] == "conflict"


@pytest.mark.functional
def test_api_loans_returns_created_loan_for_administrator(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    create_response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )
    assert create_response.status_code == 201
    created_loan_id = create_response.get_json()["data"]["id"]

    list_response = client.get("/api/v1/loans")
    assert list_response.status_code == 200

    loans = list_response.get_json()["data"]
    returned_ids = [loan["id"] for loan in loans]
    assert created_loan_id in returned_ids


@pytest.mark.functional
def test_admin_can_return_active_loan_and_restore_jigsaw_status(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    before_count = _count_audit_events(app)
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    create_response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": jigsaw_id,
        },
    )
    assert create_response.status_code == 201
    loan_id = create_response.get_json()["data"]["id"]

    return_response = client.post(f"/api/v1/loans/{loan_id}/return", headers=_csrf_headers(), json={})
    assert return_response.status_code == 200
    returned_payload = return_response.get_json()["data"]
    assert returned_payload["status"] == "returned"
    assert returned_payload["returned_at"] is not None

    with app.app_context():
        db_session = get_session()
        returned_loan = db_session.get(Loan, loan_id)
        assert returned_loan is not None
        assert returned_loan.status == LoanStatus.RETURNED
        assert returned_loan.returned_at is not None

        jigsaw = db_session.get(Jigsaw, jigsaw_id)
        assert jigsaw is not None
        assert jigsaw.status == JigsawStatus.AVAILABLE

    assert _count_audit_events(app) == before_count + 2


@pytest.mark.functional
def test_return_loan_rejects_already_returned_loan(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    create_response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": seeded_identity_data["available_jigsaw_id"],
        },
    )
    assert create_response.status_code == 201
    loan_id = create_response.get_json()["data"]["id"]

    first_return_response = client.post(f"/api/v1/loans/{loan_id}/return", headers=_csrf_headers(), json={})
    assert first_return_response.status_code == 200

    second_return_response = client.post(f"/api/v1/loans/{loan_id}/return", headers=_csrf_headers(), json={})
    assert second_return_response.status_code == 409
    assert second_return_response.get_json()["error"]["code"] == "conflict"


@pytest.mark.functional
def test_admin_can_edit_existing_jigsaw_fields(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.patch(
        f"/api/v1/jigsaws/{seeded_identity_data['available_jigsaw_id']}",
        headers=_csrf_headers(),
        json={
            "title": "Harbor Sunrise",
            "series_name": "My Haven Series",
            "series_number": "10",
            "piece_count": 1200,
            "condition": "excellent",
            "status": "maintenance",
            "tags": "coast,dawn",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["title"] == "Harbor Sunrise"
    assert payload["series_name"] == "My Haven Series"
    assert payload["series_number"] == "10"
    assert payload["piece_count"] == 1200
    assert payload["condition"] == "excellent"
    assert payload["status"] == "maintenance"
    assert payload["tags"] == "coast,dawn"


@pytest.mark.functional
def test_admin_can_create_jigsaw_with_extended_metadata(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={
            "title": "English Harbour",
            "series_name": "Collector Series",
            "series_number": "12",
            "manufacturer": "Gibsons",
            "artist": "Trevor Mitchell",
            "dimensions_cm": "68 x 49 cm",
            "description": "A coastal harbour scene with vintage cars and boats.",
            "piece_count": 1000,
            "condition": "excellent",
            "status": "available",
            "tags": "harbour,coast",
            "last_completed_at": "2026-06-20T14:00:00+00:00",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["series_name"] == "Collector Series"
    assert payload["series_number"] == "12"
    assert payload["manufacturer"] == "Gibsons"
    assert payload["artist"] == "Trevor Mitchell"
    assert payload["dimensions_cm"] == "68 x 49 cm"
    assert payload["description"] == "A coastal harbour scene with vintage cars and boats."
    assert payload["last_completed_at"] is not None


@pytest.mark.functional
@pytest.mark.parametrize(
    ("override_payload", "expected_field", "expected_issue_fragment"),
    [
        ({"title": "x" * 256}, "title", "255 characters or fewer"),
        ({"piece_count": "1000a"}, "piece_count", "positive integer or empty"),
        ({"piece_count": 0}, "piece_count", "greater than zero when provided"),
        ({"status": "unknown"}, "status", "must be one of"),
        ({"series_name": "s" * 256}, "series_name", "255 characters or fewer"),
        ({"series_number": "n" * 65}, "series_number", "64 characters or fewer"),
        ({"manufacturer": "m" * 256}, "manufacturer", "255 characters or fewer"),
        ({"artist": "a" * 256}, "artist", "255 characters or fewer"),
        ({"dimensions_cm": "d" * 65}, "dimensions_cm", "64 characters or fewer"),
        ({"description": "z" * 4001}, "description", "4000 characters or fewer"),
        ({"condition": "c" * 65}, "condition", "64 characters or fewer"),
        ({"tags": "t" * 513}, "tags", "512 characters or fewer"),
        ({"last_completed_at": "not-a-datetime"}, "last_completed_at", "valid ISO 8601 datetime"),
    ],
)
def test_create_jigsaw_validates_all_displayed_fields(
    client, seeded_identity_data, override_payload, expected_field, expected_issue_fragment
):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    payload = {
        "title": "Validation Base",
        "series_name": "Series Base",
        "series_number": "7",
        "manufacturer": "Ravensburger",
        "artist": "Art Poulin",
        "dimensions_cm": "70x50",
        "description": "Base description",
        "piece_count": 1000,
        "condition": "Used",
        "status": "available",
        "tags": "base",
        "last_completed_at": "2026-06-20T14:00:00+00:00",
    }
    payload.update(override_payload)

    response = client.post("/api/v1/jigsaws", headers=_csrf_headers(), json=payload)

    assert response.status_code == 422
    error_payload = response.get_json()
    assert error_payload["error"]["code"] == "validation_error"
    assert error_payload["error"]["details"][0]["field"] == expected_field
    assert expected_issue_fragment in error_payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_admin_can_create_jigsaw_with_all_empty_fields(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={
            "title": "",
            "series_name": "",
            "series_number": "",
            "manufacturer": "",
            "artist": "",
            "dimensions_cm": "",
            "description": "",
            "piece_count": "",
            "condition": "",
            "status": "",
            "tags": "",
            "last_completed_at": "",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["title"] is None
    assert payload["series_name"] is None
    assert payload["series_number"] is None
    assert payload["manufacturer"] is None
    assert payload["artist"] is None
    assert payload["dimensions_cm"] is None
    assert payload["description"] is None
    assert payload["piece_count"] is None
    assert payload["condition"] is None
    assert payload["status"] == "available"
    assert payload["tags"] is None
    assert payload["last_completed_at"] is None


@pytest.mark.functional
def test_admin_can_create_duplicate_jigsaw_titles(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    create_one = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={"title": "Duplicate Allowed", "piece_count": 500, "status": "available"},
    )
    assert create_one.status_code == 201

    create_two = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={"title": "Duplicate Allowed", "piece_count": 750, "status": "available"},
    )
    assert create_two.status_code == 201


@pytest.mark.functional
@pytest.mark.parametrize(
    ("patch_payload", "expected_field", "expected_issue_fragment"),
    [
        ({"piece_count": "letters"}, "piece_count", "must be greater than zero"),
        ({"series_name": "s" * 256}, "series_name", "255 characters or fewer"),
        ({"series_number": "n" * 65}, "series_number", "64 characters or fewer"),
        ({"manufacturer": "m" * 256}, "manufacturer", "255 characters or fewer"),
        ({"artist": "a" * 256}, "artist", "255 characters or fewer"),
        ({"dimensions_cm": "d" * 65}, "dimensions_cm", "64 characters or fewer"),
        ({"description": "z" * 4001}, "description", "4000 characters or fewer"),
        ({"condition": "c" * 65}, "condition", "64 characters or fewer"),
        ({"tags": "t" * 513}, "tags", "512 characters or fewer"),
        ({"last_completed_at": "2026/06/20"}, "last_completed_at", "valid ISO 8601 datetime"),
    ],
)
def test_update_jigsaw_validates_displayed_fields(
    client, seeded_identity_data, patch_payload, expected_field, expected_issue_fragment
):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.patch(
        f"/api/v1/jigsaws/{seeded_identity_data['available_jigsaw_id']}",
        headers=_csrf_headers(),
        json=patch_payload,
    )

    assert response.status_code == 422
    error_payload = response.get_json()
    assert error_payload["error"]["code"] == "validation_error"
    assert error_payload["error"]["details"][0]["field"] == expected_field
    assert expected_issue_fragment in error_payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_admin_can_upload_and_list_jigsaw_images(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    upload_response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "box front",
            "image": (BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), "box-front.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 201
    uploaded = upload_response.get_json()["data"]
    assert uploaded["tag"] == "Box front"
    assert uploaded["mime_type"] == "image/png"
    assert uploaded["content_url"].endswith("/content")

    list_response = client.get(f"/api/v1/jigsaws/{jigsaw_id}/images")
    assert list_response.status_code == 200
    images = list_response.get_json()["data"]
    assert len(images) == 1
    assert images[0]["id"] == uploaded["id"]

    content_response = client.get(uploaded["content_url"])
    assert content_response.status_code == 200
    assert content_response.mimetype == "image/png"


@pytest.mark.functional
def test_admin_can_upload_jigsaw_image_without_tag(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "image": (BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), "untagged.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["tag"] == "untagged"


@pytest.mark.functional
def test_upload_jigsaw_image_ignores_duplicate_content_hash(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    image_bytes = b"\x89PNG\r\n\x1a\n" + (b"d" * 128)

    first_response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "image": (BytesIO(image_bytes), "first-name.png", "image/png"),
        },
        content_type="multipart/form-data",
    )
    assert first_response.status_code == 201
    first_image = first_response.get_json()["data"]

    duplicate_response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "image": (BytesIO(image_bytes), "second-name.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert duplicate_response.status_code == 200
    duplicate_image = duplicate_response.get_json()["data"]
    assert duplicate_image["id"] == first_image["id"]

    list_response = client.get(f"/api/v1/jigsaws/{jigsaw_id}/images")
    assert list_response.status_code == 200
    images = list_response.get_json()["data"]
    assert len(images) == 1


@pytest.mark.functional
def test_admin_can_permanently_delete_jigsaw_and_images(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    upload_response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "image": (BytesIO(b"\x89PNG\r\n\x1a\n" + b"p" * 64), "delete-me.png", "image/png"),
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    content_url = upload_response.get_json()["data"]["content_url"]

    delete_response = client.delete(f"/api/v1/jigsaws/{jigsaw_id}/permanent", headers=_csrf_headers())
    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["deleted"] is True

    get_jigsaw_response = client.get(f"/api/v1/jigsaws/{jigsaw_id}")
    assert get_jigsaw_response.status_code == 404

    get_content_response = client.get(content_url)
    assert get_content_response.status_code == 404


@pytest.mark.functional
def test_permanent_delete_cascades_related_loans(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    first_loan_response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": jigsaw_id,
        },
    )
    assert first_loan_response.status_code == 201
    first_loan_id = first_loan_response.get_json()["data"]["id"]

    return_response = client.post(f"/api/v1/loans/{first_loan_id}/return", headers=_csrf_headers(), json={})
    assert return_response.status_code == 200

    second_loan_response = client.post(
        "/api/v1/loans",
        headers=_csrf_headers(),
        json={
            "borrower_user_id": seeded_identity_data["borrower_user_id"],
            "jigsaw_id": jigsaw_id,
        },
    )
    assert second_loan_response.status_code == 201

    delete_response = client.delete(f"/api/v1/jigsaws/{jigsaw_id}/permanent", headers=_csrf_headers())
    assert delete_response.status_code == 200

    list_response = client.get("/api/v1/loans")
    assert list_response.status_code == 200
    remaining_loan_jigsaw_ids = {loan["jigsaw_id"] for loan in list_response.get_json()["data"]}
    assert jigsaw_id not in remaining_loan_jigsaw_ids


@pytest.mark.functional
def test_admin_can_upload_larger_jigsaw_image_payload(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]
    large_png_payload = b"\x89PNG\r\n\x1a\n" + (b"x" * 200_000)

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "completed puzzle",
            "image": (BytesIO(large_png_payload), "completed.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["mime_type"] == "image/png"


@pytest.mark.functional
def test_upload_jigsaw_image_rejects_non_image_mime_type(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "notes",
            "image": (BytesIO(b"not-an-image"), "notes.txt", "text/plain"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "image"
    assert payload["error"]["details"][0]["issue"] == "must be an image content type"


@pytest.mark.functional
def test_upload_jigsaw_image_rejects_empty_file(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "empty",
            "image": (BytesIO(b""), "empty.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "image"
    assert payload["error"]["details"][0]["issue"] == "file must not be empty"


@pytest.mark.functional
def test_upload_jigsaw_image_rejects_payload_larger_than_limit(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]
    too_large_payload = b"\x89PNG\r\n\x1a\n" + (b"x" * (8 * 1024 * 1024 + 1))

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "too large",
            "image": (BytesIO(too_large_payload), "too-large.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "image"
    assert "bytes or fewer" in payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_upload_jigsaw_image_rejects_tag_that_is_too_long(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]

    response = client.post(
        f"/api/v1/jigsaws/{jigsaw_id}/images",
        headers=_csrf_headers(),
        data={
            "tag": "t" * 65,
            "image": (BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), "tag-too-long.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "tag"
    assert "64 characters or fewer" in payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_borrower_cannot_list_jigsaw_images(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get(f"/api/v1/jigsaws/{seeded_identity_data['available_jigsaw_id']}/images")

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_api_get_jigsaw_hides_retired_from_borrower(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get(f"/api/v1/jigsaws/{seeded_identity_data['retired_jigsaw_id']}")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["code"] == "not_found"


@pytest.mark.functional
def test_api_create_jigsaw_requires_admin_role(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.post(
        "/api/v1/jigsaws",
        headers=_csrf_headers(),
        json={"title": "No Access", "piece_count": 100, "status": "available"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_api_rejects_unknown_session_user(client, seeded_identity_data):
    _set_user_session(client, 999999)

    response = client.get("/api/v1/jigsaws")

    _assert_authentication_required(response)


@pytest.mark.functional
def test_api_rejects_inactive_user_session(app, client, seeded_identity_data):
    with app.app_context():
        db_session = get_session()
        borrower_user = db_session.query(User).filter_by(email="borrower@example.com").one()
        borrower_user.is_active = False
        db_session.commit()

    _set_user_session(client, seeded_identity_data["borrower_user_id"])
    response = client.get("/api/v1/jigsaws")

    _assert_authentication_required(response)


@pytest.mark.functional
def test_auth_login_rejects_unknown_credentials(client, seeded_identity_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "Nope123456!"},
    )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["code"] == "authentication_failed"


@pytest.mark.functional
def test_auth_login_sets_session_and_csrf_token(client, seeded_identity_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["user"]["email"] == "admin@example.com"
    assert payload["data"]["user"]["roles"] == ["administrator"]
    assert isinstance(payload["data"]["csrf_token"], str)
    assert payload["data"]["csrf_token"]


@pytest.mark.functional
def test_auth_me_returns_authenticated_user(client, seeded_identity_data):
    client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )

    me_response = client.get("/api/v1/auth/me")

    assert me_response.status_code == 200
    payload = me_response.get_json()
    assert payload["data"]["user"]["email"] == "borrower@example.com"
    assert payload["data"]["user"]["roles"] == ["borrower"]
    assert isinstance(payload["data"]["csrf_token"], str)
    assert payload["data"]["csrf_token"]

    csrf_token = payload["data"]["csrf_token"]

    protected_mutation = client.post(
        "/api/v1/jigsaws",
        headers={"X-CSRF-Token": csrf_token},
        json={"title": "Try", "piece_count": 500, "status": "available"},
    )
    assert protected_mutation.status_code == 403
    assert protected_mutation.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_auth_me_generates_csrf_token_if_session_missing_one(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"], csrf_token="")

    with client.session_transaction() as test_session:
        test_session.pop("csrf_token", None)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    csrf_token = response.get_json()["data"]["csrf_token"]
    assert isinstance(csrf_token, str)
    assert csrf_token

    with client.session_transaction() as test_session:
        assert test_session["csrf_token"] == csrf_token


@pytest.mark.functional
def test_mutation_endpoint_rejects_missing_or_invalid_csrf(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"], csrf_token="expected-token")

    missing_header_response = client.post(
        "/api/v1/jigsaws",
        json={"title": "Missing CSRF", "piece_count": 300, "status": "available"},
    )
    assert missing_header_response.status_code == 403
    assert missing_header_response.get_json()["error"]["code"] == "forbidden"

    wrong_header_response = client.post(
        "/api/v1/jigsaws",
        headers={"X-CSRF-Token": "wrong-token"},
        json={"title": "Bad CSRF", "piece_count": 300, "status": "available"},
    )
    assert wrong_header_response.status_code == 403
    assert wrong_header_response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_auth_logout_requires_csrf_and_clears_session(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    logout_without_csrf = client.post("/api/v1/auth/logout")
    assert logout_without_csrf.status_code == 403
    assert logout_without_csrf.get_json()["error"]["code"] == "forbidden"

    logout_response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_response.status_code == 200
    assert logout_response.get_json()["data"]["logged_out"] is True

    post_logout_response = client.get("/api/v1/auth/me")
    _assert_authentication_required(post_logout_response)


@pytest.mark.functional
def test_auth_login_rejects_wrong_password(client, seeded_identity_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "WrongPassword999!"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_failed"


@pytest.mark.functional
def test_auth_login_accepts_existing_user_email_without_dot_domain(app, client, seeded_identity_data):
    with app.app_context():
        db_session = get_session()
        borrower_role = db_session.query(Role).filter_by(name="borrower").one()

        local_domain_user = User(email="borrower@localhost", display_name="Borrower Local", is_active=True)
        local_domain_user.set_password("BorrowerLocal123!")
        db_session.add(local_domain_user)
        db_session.flush()
        db_session.add(UserRole(user_id=local_domain_user.id, role_id=borrower_role.id))
        db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@localhost", "password": "BorrowerLocal123!"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["user"]["email"] == "borrower@localhost"


@pytest.mark.functional
def test_audit_events_requires_admin_role(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["borrower_user_id"])

    response = client.get("/api/v1/audit-events")

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_audit_events_returns_recent_activity(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "audit.target@example.com",
            "password": "AuditTargetPass123!",
            "display_name": "Audit Target",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    response = client.get("/api/v1/audit-events?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) >= 1
    assert payload["data"][0]["action"]
    assert payload["data"][0]["created_at"]


@pytest.mark.functional
def test_audit_events_rejects_invalid_limit(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.get("/api/v1/audit-events?limit=999")

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.functional
def test_create_user_rejects_overlong_email(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    long_email = f"{'a' * 250}@example.com"

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": long_email,
            "password": "BigEmailPass123!",
            "display_name": "Big Email",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "email"
    assert "255 characters or fewer" in payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_create_user_rejects_invalid_email_injection_pattern(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "admin@example.com' OR '1'='1",
            "password": "SqlPayloadPass123!",
            "display_name": "SQL payload",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "email"
    assert payload["error"]["details"][0]["issue"] == "must be a valid email address"


@pytest.mark.functional
def test_create_user_rejects_script_tag_in_display_name(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "script.user@example.com",
            "password": "ScriptNamePass123!",
            "display_name": "<script>alert(1)</script>",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "display_name"


@pytest.mark.functional
def test_update_user_rejects_control_characters_in_display_name(app, client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    with app.app_context():
        db_session = get_session()
        borrower_user = db_session.query(User).filter_by(email="borrower@example.com").one()
        borrower_user_id = borrower_user.id

    response = client.patch(
        f"/api/v1/users/{borrower_user_id}",
        headers=_csrf_headers(),
        json={"display_name": "bad\nname"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.functional
def test_login_rejects_overlong_password(client, seeded_identity_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a" * 300},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.functional
def test_create_user_requires_password(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "no.password@example.com",
            "display_name": "No Password",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "password"


@pytest.mark.functional
def test_create_user_rejects_password_shorter_than_minimum(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/users",
        headers=_csrf_headers(),
        json={
            "email": "short.password@example.com",
            "password": "TooShort1!",
            "display_name": "Short Password",
            "is_active": True,
            "roles": ["borrower"],
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "password"
    assert "at least 12 characters" in payload["error"]["details"][0]["issue"]


@pytest.mark.functional
def test_update_user_rejects_self_deactivation(client, seeded_identity_data):
    _set_user_session(client, seeded_identity_data["admin_user_id"])

    response = client.patch(
        f"/api/v1/users/{seeded_identity_data['admin_user_id']}",
        headers=_csrf_headers(),
        json={"is_active": False},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"


@pytest.mark.functional
def test_auth_me_patch_updates_display_name(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
        json={"display_name": "Borrower Renamed"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["user"]["display_name"] == "Borrower Renamed"


@pytest.mark.functional
def test_auth_me_patch_updates_password(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    update_response = client.patch(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "current_password": "BorrowerPassword123!",
            "new_password": "BorrowerPassword456!",
        },
    )
    assert update_response.status_code == 200

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword456!"},
    )
    assert new_login_response.status_code == 200


@pytest.mark.functional
def test_auth_me_patch_rejects_email_change(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "new@example.com"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.functional
def test_auth_me_patch_rejects_incorrect_current_password(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "current_password": "WrongPassword999!",
            "new_password": "BorrowerPassword456!",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_auth_me_patch_rejects_new_password_shorter_than_minimum(client, seeded_identity_data):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "current_password": "BorrowerPassword123!",
            "new_password": "short1!",
        },
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"][0]["field"] == "password"
    assert "at least 12 characters" in payload["error"]["details"][0]["issue"]
