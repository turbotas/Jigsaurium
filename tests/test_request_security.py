import pytest

from app.db import get_session
from app.models import BlockedIp
from app.request_security import (
    reset_request_security_state,
    resolve_client_request_context,
    resolve_console_log_ip,
)


@pytest.mark.functional
def test_resolve_client_request_context_ignores_untrusted_forwarded_headers():
    context = resolve_client_request_context(
        remote_addr="198.51.100.20",
        forwarded_header='for="203.0.113.11"',
        x_forwarded_for_header="203.0.113.11",
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=None,
    )

    assert context.remote_addr == "198.51.100.20"
    assert context.client_ip_resolved == "198.51.100.20"
    assert context.forwarded_chain is None


@pytest.mark.functional
def test_resolve_client_request_context_uses_forwarded_chain_for_trusted_proxy():
    context = resolve_client_request_context(
        remote_addr="192.168.51.12",
        forwarded_header='for="203.0.113.11";proto=https, for="192.168.51.99"',
        x_forwarded_for_header=None,
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=None,
    )

    assert context.remote_addr == "192.168.51.12"
    assert context.client_ip_resolved == "203.0.113.11"
    assert context.forwarded_chain == "203.0.113.11, 192.168.51.99"


@pytest.mark.functional
def test_resolve_client_request_context_uses_trusted_proxy_hops_from_right():
    context = resolve_client_request_context(
        remote_addr="192.168.51.12",
        forwarded_header=None,
        x_forwarded_for_header="198.51.100.7, 203.0.113.11",
        trusted_proxy_cidrs=[],
        trusted_proxy_hops=1,
    )

    assert context.client_ip_resolved == "203.0.113.11"


@pytest.mark.functional
def test_resolve_client_request_context_prefers_trusted_proxy_cidrs_when_both_modes_set():
    context = resolve_client_request_context(
        remote_addr="192.168.51.12",
        forwarded_header='for="203.0.113.11";proto=https, for="192.168.51.99"',
        x_forwarded_for_header=None,
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=1,
    )

    assert context.client_ip_resolved == "203.0.113.11"


@pytest.mark.functional
def test_resolve_client_request_context_requires_trusted_remote_when_cidrs_configured():
    context = resolve_client_request_context(
        remote_addr="198.51.100.20",
        forwarded_header='for="203.0.113.11"',
        x_forwarded_for_header=None,
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=1,
    )

    assert context.client_ip_resolved == "198.51.100.20"


@pytest.mark.functional
def test_resolve_console_log_ip_prefers_forwarded_value_for_trusted_proxy():
    resolved_ip = resolve_console_log_ip(
        remote_addr="192.168.51.12",
        forwarded_header='for="203.0.113.11";proto=https, for="192.168.51.99"',
        x_forwarded_for_header=None,
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=None,
    )

    assert resolved_ip == "203.0.113.11"


@pytest.mark.functional
def test_resolve_console_log_ip_ignores_forwarded_value_for_untrusted_proxy():
    resolved_ip = resolve_console_log_ip(
        remote_addr="198.51.100.20",
        forwarded_header='for="203.0.113.11"',
        x_forwarded_for_header="203.0.113.11",
        trusted_proxy_cidrs=["192.168.51.0/24"],
        trusted_proxy_hops=None,
    )

    assert resolved_ip == "198.51.100.20"


@pytest.mark.functional
def test_request_ban_triggers_after_five_consecutive_404(client, app):
    reset_request_security_state()
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.51.0/24"]
    proxy_remote_addr = "192.168.51.12"
    headers = {"X-Forwarded-For": "203.0.113.77"}

    for _ in range(5):
        response = client.get(
            "/definitely-not-found",
            headers=headers,
            environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
        )
        assert response.status_code == 404

    blocked = client.get(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
    )

    assert blocked.status_code == 429
    retry_after = int(blocked.headers["Retry-After"])
    assert retry_after > 86000
    assert retry_after <= 86400


@pytest.mark.functional
def test_request_ban_requires_consecutive_404_streak(client, app):
    reset_request_security_state()
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.51.0/24"]
    proxy_remote_addr = "192.168.51.12"
    headers = {"X-Forwarded-For": "203.0.113.88"}
    request_kwargs = {
        "headers": headers,
        "environ_overrides": {"REMOTE_ADDR": proxy_remote_addr},
    }

    for _ in range(4):
        assert client.get("/missing-before-reset", **request_kwargs).status_code == 404

    assert client.get("/", **request_kwargs).status_code == 200

    for _ in range(4):
        assert client.get("/missing-after-reset", **request_kwargs).status_code == 404

    assert client.get("/", **request_kwargs).status_code == 200


@pytest.mark.functional
def test_request_ban_skips_trusted_client_cidrs(client, app):
    reset_request_security_state()
    app.config["TRUSTED_PROXY_CIDRS"] = ["192.168.51.0/24"]
    app.config["TRUSTED_CLIENT_CIDRS"] = ["203.0.113.0/24"]
    proxy_remote_addr = "192.168.51.12"
    headers = {"X-Forwarded-For": "203.0.113.77"}

    for _ in range(8):
        response = client.get(
            "/trusted-client-missing-path",
            headers=headers,
            environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
        )
        assert response.status_code == 404

    allowed = client.get(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": proxy_remote_addr},
    )
    assert allowed.status_code == 200

    with app.app_context():
        db_session = get_session()
        row = db_session.query(BlockedIp).filter_by(ip_address="203.0.113.77").one_or_none()
        assert row is None
