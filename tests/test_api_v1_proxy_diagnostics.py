"""Tests for GET /api/v1/system/proxy-diagnostics and the proxy-header probe analysis.

Each scenario simulates what a reverse proxy forwards to the app after the admin UI sent the
probe headers: `Forwarded: for=192.0.2.1;...`, `X-Forwarded-For: 192.0.2.2`,
`X-Forwarded-Host: <host>:1` and `X-Forwarded-Proto: http`.
"""

import pytest

from app.db import get_session
from app.models import Role, User, UserRole
from app.request_security import analyse_proxy_header_probe

PATH = "/api/v1/system/proxy-diagnostics"
PROXY_IP = "192.168.100.12"
CLIENT_IP = "203.0.113.50"
HOST = "www.example.test"
PROBE_FORWARDED = f'for=192.0.2.1;proto=http;host="{HOST}:1"'


TYPICAL_PROXY_HEADERS = {
    "Forwarded": PROBE_FORWARDED,
    "X-Forwarded-For": f"192.0.2.2, {CLIENT_IP}",
    "X-Forwarded-Proto": "http",
    "X-Forwarded-Host": f"{HOST}:1",
}


def _analyse(headers, *, header_mode="x-forwarded", cidrs=(f"{PROXY_IP}/32",), remote=PROXY_IP, **settings):
    return analyse_proxy_header_probe(
        remote_addr=remote,
        headers={"X-Jigsaurium-Proxy-Probe": "1", **headers},
        trusted_proxy_cidrs=list(cidrs),
        trusted_proxy_hops=None,
        trusted_proxy_header=header_mode,
        probe_host=HOST,
        **settings,
    )


def _check(result, check_id):
    return next(check for check in result["checks"] if check["id"] == check_id)


@pytest.mark.functional
def test_typical_nginx_appends_xff_and_passes_forwarded_through():
    # proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; Proto/Host set; Forwarded untouched.
    result = _analyse(
        {
            "Forwarded": PROBE_FORWARDED,
            "X-Forwarded-For": f"192.0.2.2, {CLIENT_IP}",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": HOST,
        }
    )

    assert result["findings"] == {
        "forwarded": "passed_through",
        "x_forwarded_for": "appended",
        "x_forwarded_proto": "overwritten",
        "x_forwarded_host": "overwritten",
    }
    assert result["recommended_trusted_proxy_header"] == "x-forwarded"
    assert result["verdict"] == "ok"
    assert result["resolved_client_ip"] == CLIENT_IP
    assert result["messages"] == []


@pytest.mark.functional
def test_forwarded_mode_is_unsafe_when_proxy_passes_forwarded_through():
    result = _analyse(
        {"Forwarded": PROBE_FORWARDED, "X-Forwarded-For": f"192.0.2.2, {CLIENT_IP}"},
        header_mode="forwarded",
    )

    assert result["verdict"] == "unsafe"
    assert result["recommended_trusted_proxy_header"] == "x-forwarded"
    assert result["resolved_client_ip"] == "192.0.2.1"
    check = _check(result, "visitor_address_trusted")
    assert check["passed"] is False
    assert "Set TRUSTED_PROXY_HEADER=x-forwarded" in check["detail"]
    assert result["messages"] == ["Visitors could fake their address."]


@pytest.mark.functional
def test_proxy_overwriting_only_forwarded_recommends_forwarded_mode():
    result = _analyse(
        {"Forwarded": f'for={CLIENT_IP};proto=https;host="{HOST}"', "X-Forwarded-For": "192.0.2.2"},
        header_mode="forwarded",
    )

    assert result["findings"]["forwarded"] == "overwritten"
    assert result["findings"]["x_forwarded_for"] == "passed_through"
    assert result["recommended_trusted_proxy_header"] == "forwarded"
    assert result["verdict"] == "ok"


@pytest.mark.functional
def test_no_trustworthy_client_ip_header_is_unsafe():
    result = _analyse({"Forwarded": PROBE_FORWARDED, "X-Forwarded-For": "192.0.2.2"})

    assert result["recommended_trusted_proxy_header"] is None
    assert result["verdict"] == "unsafe"


@pytest.mark.functional
def test_passed_through_host_and_proto_do_not_affect_the_verdict():
    result = _analyse(
        {
            "X-Forwarded-For": CLIENT_IP,
            "X-Forwarded-Proto": "http",
            "X-Forwarded-Host": f"{HOST}:1",
        }
    )

    assert result["findings"]["x_forwarded_for"] == "overwritten"
    assert result["findings"]["forwarded"] == "stripped"
    assert result["findings"]["x_forwarded_proto"] == "passed_through"
    assert result["findings"]["x_forwarded_host"] == "passed_through"
    assert result["verdict"] == "ok"
    assert result["messages"] == []


@pytest.mark.functional
def test_untrusted_remote_address_is_reported():
    result = _analyse({"X-Forwarded-For": f"192.0.2.2, {CLIENT_IP}"}, remote="172.18.0.1")

    assert result["remote_is_trusted_proxy"] is False
    assert result["resolved_client_ip"] == "172.18.0.1"
    assert result["verdict"] == "unsafe"
    check = _check(result, "arrived_via_proxy")
    assert check["passed"] is False
    assert "not in TRUSTED_PROXY_CIDRS" in check["detail"]


@pytest.mark.functional
def test_current_test_environment_shape_is_healthy():
    # Nginx Proxy Manager: appends X-Forwarded-For, passes Forwarded/Host/Proto through.
    result = _analyse(TYPICAL_PROXY_HEADERS, cidrs=("192.168.51.12/32", "172.16.0.0/12"), remote="172.16.4.1")

    assert result["verdict"] == "ok"
    assert all(check["passed"] is True for check in result["checks"])
    assert [check["id"] for check in result["checks"]] == [
        "proxy_only_access",
        "arrived_via_proxy",
        "visitor_address_trusted",
        "proxy_range_excludes_visitors",
        "secure_cookies",
        "hsts",
    ]


@pytest.mark.functional
def test_proxy_only_access_switched_off_is_a_problem():
    result = _analyse(TYPICAL_PROXY_HEADERS, require_trusted_proxy=False)

    assert result["verdict"] == "unsafe"
    assert _check(result, "proxy_only_access")["passed"] is False


@pytest.mark.functional
def test_empty_trusted_proxy_range_is_a_problem():
    result = _analyse(TYPICAL_PROXY_HEADERS, cidrs=())

    assert result["verdict"] == "unsafe"
    assert _check(result, "proxy_only_access")["passed"] is False
    assert _check(result, "arrived_via_proxy")["passed"] is False


@pytest.mark.functional
def test_trusted_range_covering_visitors_is_a_problem():
    result = _analyse(TYPICAL_PROXY_HEADERS, cidrs=(f"{PROXY_IP}/32", "203.0.113.0/24"))

    assert result["verdict"] == "unsafe"
    # The real visitor address is skipped as a "proxy", so the fake probe value wins.
    assert result["resolved_client_ip"] == "192.0.2.2"
    check = _check(result, "proxy_range_excludes_visitors")
    assert check["passed"] is False
    assert "fake value" in check["detail"]


@pytest.mark.functional
def test_range_check_is_skipped_when_visitor_address_cannot_be_trusted():
    result = _analyse({"X-Forwarded-For": "192.0.2.2"})

    assert _check(result, "proxy_range_excludes_visitors")["passed"] is None
    assert result["verdict"] == "unsafe"


@pytest.mark.functional
@pytest.mark.parametrize(
    "settings, failing",
    [
        ({"allow_insecure_http": True, "session_cookie_secure": False}, {"secure_cookies", "hsts"}),
        ({"session_cookie_secure": False}, {"secure_cookies"}),
        ({"hsts_max_age_seconds": 0}, {"hsts"}),
    ],
)
def test_insecure_app_settings_are_a_problem(settings, failing):
    result = _analyse(TYPICAL_PROXY_HEADERS, **settings)

    assert result["verdict"] == "unsafe"
    assert {check["id"] for check in result["checks"] if check["passed"] is False} == failing


@pytest.mark.functional
def test_dev_settings_without_insecure_http_are_healthy():
    # The checks follow the real cookie/HSTS settings, not APP_ENV: a proxied dev is healthy.
    result = _analyse(TYPICAL_PROXY_HEADERS, allow_insecure_http=False, session_cookie_secure=True)

    assert result["verdict"] == "ok"


@pytest.mark.functional
def test_without_probe_header_no_findings_are_reported():
    result = analyse_proxy_header_probe(
        remote_addr=PROXY_IP,
        headers={"X-Forwarded-For": CLIENT_IP},
        trusted_proxy_cidrs=[f"{PROXY_IP}/32"],
        trusted_proxy_hops=None,
        trusted_proxy_header="x-forwarded",
        probe_host=HOST,
    )

    assert result["probe_sent"] is False
    assert result["findings"] == {}
    assert result["verdict"] == "unknown"


@pytest.fixture()
def users(app):
    with app.app_context():
        db_session = get_session()
        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        member_role = db_session.query(Role).filter_by(name="member").one()
        admin = User(email="admin@example.com", display_name="Admin")
        member = User(email="member@example.com", display_name="Member")
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


def _login(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["csrf_token"] = "test-csrf-token"


@pytest.mark.functional
def test_proxy_diagnostics_requires_administrator(client, users):
    assert client.get(PATH).status_code == 401

    _login(client, users["member"])
    assert client.get(PATH).status_code == 403


@pytest.mark.functional
def test_proxy_diagnostics_endpoint_reports_probe_findings(app, client, users):
    app.config["TRUSTED_PROXY_CIDRS"] = [f"{PROXY_IP}/32"]
    app.config["SESSION_COOKIE_SECURE"] = True
    _login(client, users["admin"])

    response = client.get(
        f"{PATH}?probe_host=localhost",
        headers={
            "X-Jigsaurium-Proxy-Probe": "1",
            "Forwarded": 'for=192.0.2.1;proto=http;host="localhost:1"',
            "X-Forwarded-For": f"192.0.2.2, {CLIENT_IP}",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "localhost",
        },
        environ_overrides={"REMOTE_ADDR": PROXY_IP},
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()["data"]
    assert data["findings"]["forwarded"] == "passed_through"
    assert data["findings"]["x_forwarded_for"] == "appended"
    assert data["recommended_trusted_proxy_header"] == "x-forwarded"
    assert data["verdict"] == "ok"
    assert data["resolved_client_ip"] == CLIENT_IP
    assert data["resolved_scheme"] == "https"


@pytest.mark.functional
def test_proxy_diagnostics_rejects_overlong_probe_host(client, users):
    _login(client, users["admin"])

    response = client.get(f"{PATH}?probe_host={'a' * 300}")

    assert response.status_code == 422
