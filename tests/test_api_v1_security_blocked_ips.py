from datetime import datetime, timezone

import pytest

from app.db import get_session
from app.models import BlockedIp, Role, User, UserRole
from app.request_security import reset_request_security_state


@pytest.fixture()
def seeded_security_identity_data(app):
    with app.app_context():
        db_session = get_session()

        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        borrower_role = db_session.query(Role).filter_by(name="borrower").one()

        admin_user = User(email="admin.security@example.com", display_name="Admin Security")
        borrower_user = User(email="borrower.security@example.com", display_name="Borrower Security")
        admin_user.set_password("AdminSecurityPass123!")
        borrower_user.set_password("BorrowerSecurityPass123!")

        db_session.add_all([admin_user, borrower_user])
        db_session.flush()
        db_session.add_all(
            [
                UserRole(user_id=admin_user.id, role_id=admin_role.id),
                UserRole(user_id=borrower_user.id, role_id=borrower_role.id),
            ]
        )
        db_session.commit()

        seeded_ids = {
            "admin_user_id": admin_user.id,
            "borrower_user_id": borrower_user.id,
        }

    db_session.remove()
    yield seeded_ids


def _set_user_session(client, user_id, csrf_token="test-csrf-token"):
    with client.session_transaction() as test_session:
        test_session["user_id"] = user_id
        test_session["csrf_token"] = csrf_token


def _csrf_headers(csrf_token="test-csrf-token"):
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.functional
def test_admin_can_add_list_and_remove_blocked_ip(client, seeded_security_identity_data):
    _set_user_session(client, seeded_security_identity_data["admin_user_id"])

    create_response = client.post(
        "/api/v1/security/blocked-ips",
        headers=_csrf_headers(),
        json={
            "ip_address": "203.0.113.10",
            "duration_hours": 24,
            "reason": "manual test block",
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.get_json()
    assert created_payload["data"]["ip_address"] == "203.0.113.10"
    assert created_payload["data"]["block_source"] == "manual"

    list_response = client.get("/api/v1/security/blocked-ips")
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert len(list_payload["data"]) == 1
    blocked_entry = list_payload["data"][0]
    assert blocked_entry["ip_address"] == "203.0.113.10"
    assert blocked_entry["is_active"] is True

    delete_response = client.delete(
        f"/api/v1/security/blocked-ips/{blocked_entry['id']}",
        headers=_csrf_headers(),
    )
    assert delete_response.status_code == 200

    list_after_delete_response = client.get("/api/v1/security/blocked-ips")
    assert list_after_delete_response.status_code == 200
    list_after_delete_payload = list_after_delete_response.get_json()
    assert list_after_delete_payload["data"] == []


@pytest.mark.functional
def test_borrower_cannot_manage_blocked_ips(client, seeded_security_identity_data):
    _set_user_session(client, seeded_security_identity_data["borrower_user_id"])

    assert client.get("/api/v1/security/blocked-ips").status_code == 403
    assert (
        client.post(
            "/api/v1/security/blocked-ips",
            headers=_csrf_headers(),
            json={"ip_address": "203.0.113.44", "duration_hours": 24},
        ).status_code
        == 403
    )
    assert client.delete("/api/v1/security/blocked-ips/1", headers=_csrf_headers()).status_code == 403


@pytest.mark.functional
def test_borrower_cannot_manage_security_sessions(client, seeded_security_identity_data):
    _set_user_session(client, seeded_security_identity_data["borrower_user_id"])

    assert client.get("/api/v1/security/sessions").status_code == 403
    assert client.delete("/api/v1/security/sessions/1", headers=_csrf_headers()).status_code == 403


@pytest.mark.functional
def test_auto_404_streak_ban_is_persisted_in_database(client, app):
    reset_request_security_state()
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.100.0/24"]
    proxy_remote_addr = "192.168.100.12"
    headers = {"X-Forwarded-For": "203.0.113.77"}

    for _ in range(5):
        response = client.get(
            "/scanner-probe-path",
            headers=headers,
            environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
        )
        assert response.status_code == 404

    with app.app_context():
        db_session = get_session()
        row = db_session.query(BlockedIp).filter_by(ip_address="203.0.113.77").one()
        assert row.block_source == "auto_404_streak"
        assert row.block_reason == "5 consecutive 404 responses"
        assert int(row.hit_count or 0) == 1
        blocked_until = row.blocked_until
        if blocked_until.tzinfo is None:
            blocked_until = blocked_until.replace(tzinfo=timezone.utc)
        assert blocked_until > datetime.now(timezone.utc)

    blocked_response = client.get(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
    )
    assert blocked_response.status_code == 429


@pytest.mark.functional
def test_admin_cannot_block_trusted_internal_client_cidr(client, app, seeded_security_identity_data):
    app.config["TRUSTED_CLIENT_CIDRS"] = ["203.0.113.0/24"]
    _set_user_session(client, seeded_security_identity_data["admin_user_id"])

    response = client.post(
        "/api/v1/security/blocked-ips",
        headers=_csrf_headers(),
        json={
            "ip_address": "203.0.113.10",
            "duration_hours": 24,
            "reason": "should be blocked from block list",
        },
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "conflict"
