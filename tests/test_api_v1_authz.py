import pytest

from app.db import Base, get_engine, get_session
from app.models import AuditEvent, Jigsaw, Role, User, UserRole
from app.models.jigsaw import JigsawStatus


@pytest.fixture()
def seeded_identity_data(app):
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(bind=engine)

        db_session = get_session()

        admin_role = Role(name="administrator", description="Administrator")
        borrower_role = Role(name="borrower", description="Borrower")
        db_session.add_all([admin_role, borrower_role])
        db_session.flush()

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

        yield {
            "admin_user_id": admin_user.id,
            "borrower_user_id": borrower_user.id,
            "available_jigsaw_id": available_jigsaw.id,
            "retired_jigsaw_id": retired_jigsaw.id,
        }

        db_session.remove()
        Base.metadata.drop_all(bind=engine)


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
        ("GET", "/api/v1/jigsaws/1", None),
        (
            "POST",
            "/api/v1/users",
            {
                "email": "someone@example.com",
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
        ("PATCH", "/api/v1/jigsaws/1", {"title": "Updated title"}),
        ("DELETE", "/api/v1/jigsaws/1", None),
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
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "borrower@example.com", "password": "BorrowerPassword123!"},
    )
    csrf_token = login_response.get_json()["data"]["csrf_token"]

    me_response = client.get("/api/v1/auth/me")

    assert me_response.status_code == 200
    payload = me_response.get_json()
    assert payload["data"]["user"]["email"] == "borrower@example.com"
    assert payload["data"]["user"]["roles"] == ["borrower"]

    protected_mutation = client.post(
        "/api/v1/jigsaws",
        headers={"X-CSRF-Token": csrf_token},
        json={"title": "Try", "piece_count": 500, "status": "available"},
    )
    assert protected_mutation.status_code == 403
    assert protected_mutation.get_json()["error"]["code"] == "forbidden"


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
