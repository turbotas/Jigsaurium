from types import SimpleNamespace

import pytest

from app.dev_server import _resolve_remote_addr_for_log


class _StubHandler:
    def __init__(self, *, address, environ, config):
        self._address = address
        self.environ = environ
        self.server = SimpleNamespace(app=SimpleNamespace(config=config))

    def address_string(self):
        return self._address


@pytest.mark.functional
def test_resolve_remote_addr_for_log_prefers_forwarded_client_with_trusted_proxy_cidrs():
    handler = _StubHandler(
        address="192.168.51.12",
        environ={
            "REMOTE_ADDR": "192.168.51.12",
            "HTTP_FORWARDED": 'for="203.0.113.11";proto=https, for="192.168.51.99"',
        },
        config={
            "TRUSTED_PROXY_CIDRS": ["192.168.51.0/24"],
            "TRUSTED_PROXY_HOPS": 1,
        },
    )

    assert _resolve_remote_addr_for_log(handler) == "203.0.113.11"


@pytest.mark.functional
def test_resolve_remote_addr_for_log_ignores_forwarded_headers_for_untrusted_remote_addr():
    handler = _StubHandler(
        address="198.51.100.20",
        environ={
            "REMOTE_ADDR": "198.51.100.20",
            "HTTP_FORWARDED": 'for="203.0.113.11";proto=https, for="192.168.51.99"',
            "HTTP_X_FORWARDED_FOR": "203.0.113.11, 192.168.51.99",
        },
        config={
            "TRUSTED_PROXY_CIDRS": ["192.168.51.0/24"],
            "TRUSTED_PROXY_HOPS": 1,
        },
    )

    assert _resolve_remote_addr_for_log(handler) == "198.51.100.20"
