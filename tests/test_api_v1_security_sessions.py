from datetime import datetime, timedelta, timezone

import pytest

from app.db import get_session
from app.models import Role, User, UserRole, UserSession


@pytest.fixture()
def seeded_session_identity_data(app):
    with app.app_context():
        db_session = get_session()

        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        member_role = db_session.query(Role).filter_by(name="member").one()

        admin_user = User(email="admin.sessions@example.com", display_name="Admin Sessions")
        member_user = User(email="member.sessions@example.com", display_name="Member Sessions")
        admin_user.set_password("AdminSessionsPass123!")
        member_user.set_password("MemberSessionsPass123!")

        db_session.add_all([admin_user, member_user])
        db_session.flush()
        db_session.add_all(
            [
                UserRole(user_id=admin_user.id, role_id=admin_role.id),
                UserRole(user_id=member_user.id, role_id=member_role.id),
            ]
        )
        db_session.commit()

        seeded_ids = {
            "admin_email": admin_user.email,
            "admin_password": "AdminSessionsPass123!",
            "member_email": member_user.email,
            "member_password": "MemberSessionsPass123!",
        }

    db_session.remove()
    yield seeded_ids


def _login(client, *, email, password, headers=None, environ_overrides=None):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=headers or {},
        environ_overrides=environ_overrides,
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    return {
        "csrf_token": payload["csrf_token"],
        "session_identifier": payload.get("session_identifier"),
        "user": payload["user"],
    }


@pytest.mark.functional
def test_security_sessions_requires_authentication(client):
    response = client.get("/api/v1/security/sessions")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["code"] == "authentication_required"


@pytest.mark.functional
def test_member_cannot_list_or_terminate_security_sessions(app, seeded_session_identity_data):
    member_client = app.test_client()
    member_login = _login(
        member_client,
        email=seeded_session_identity_data["member_email"],
        password=seeded_session_identity_data["member_password"],
    )

    list_response = member_client.get("/api/v1/security/sessions")
    assert list_response.status_code == 403
    assert list_response.get_json()["error"]["code"] == "forbidden"

    terminate_response = member_client.delete(
        "/api/v1/security/sessions/1",
        headers={"X-CSRF-Token": member_login["csrf_token"]},
    )
    assert terminate_response.status_code == 403
    assert terminate_response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.functional
def test_admin_can_list_and_terminate_active_session_with_resolved_ip(app, seeded_session_identity_data):
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.51.0/24"]
    proxy_headers = {"X-Forwarded-For": "203.0.113.77"}
    proxy_remote = {"REMOTE_ADDR": "192.168.51.12"}

    admin_client = app.test_client()
    admin_login = _login(
        admin_client,
        email=seeded_session_identity_data["admin_email"],
        password=seeded_session_identity_data["admin_password"],
        headers=proxy_headers,
        environ_overrides=proxy_remote,
    )

    member_client = app.test_client()
    _login(
        member_client,
        email=seeded_session_identity_data["member_email"],
        password=seeded_session_identity_data["member_password"],
    )

    list_response = admin_client.get("/api/v1/security/sessions")
    assert list_response.status_code == 200
    sessions = list_response.get_json()["data"]
    assert len(sessions) >= 2

    admin_session = next(
        session for session in sessions if session["user"] and session["user"]["email"] == seeded_session_identity_data["admin_email"]
    )
    member_session = next(
        session for session in sessions if session["user"] and session["user"]["email"] == seeded_session_identity_data["member_email"]
    )
    assert admin_session["origin_ip_address"] == "203.0.113.77"
    assert admin_session["session_identifier"]
    assert admin_login["session_identifier"] == admin_session["session_identifier"]

    terminate_response = admin_client.delete(
        f"/api/v1/security/sessions/{member_session['id']}",
        headers={"X-CSRF-Token": admin_login["csrf_token"]},
    )
    assert terminate_response.status_code == 200
    assert terminate_response.get_json()["data"]["terminated"] is True

    member_auth_check = member_client.get("/api/v1/auth/me")
    assert member_auth_check.status_code == 401


@pytest.mark.functional
def test_inactive_session_expires_after_idle_timeout(client, app, seeded_session_identity_data):
    _login(
        client,
        email=seeded_session_identity_data["admin_email"],
        password=seeded_session_identity_data["admin_password"],
    )

    with app.app_context():
        db_session = get_session()
        active_session = db_session.query(UserSession).order_by(UserSession.id.desc()).first()
        assert active_session is not None
        active_session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=121)
        db_session.commit()
        session_id = active_session.id

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    with app.app_context():
        db_session = get_session()
        expired_session = db_session.get(UserSession, session_id)
        assert expired_session is not None
        assert expired_session.terminated_at is not None
        assert expired_session.termination_reason == "expired"
