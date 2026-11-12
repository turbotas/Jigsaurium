from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
import threading
from urllib.parse import urlsplit

from sqlalchemy import select

from app.models.blocked_ip import BlockedIp


TRUSTED_PROXY_HEADER_X_FORWARDED = "x-forwarded"
TRUSTED_PROXY_HEADER_FORWARDED = "forwarded"
TRUSTED_PROXY_HEADER_CHOICES = (TRUSTED_PROXY_HEADER_X_FORWARDED, TRUSTED_PROXY_HEADER_FORWARDED)
DEFAULT_TRUSTED_PROXY_HEADER = TRUSTED_PROXY_HEADER_X_FORWARDED

REQUEST_BAN_TRIGGER_404_STREAK = 5
REQUEST_BAN_DURATION_SECONDS = 24 * 60 * 60
AUTO_BLOCK_SOURCE = "auto_404_streak"
MANUAL_BLOCK_SOURCE = "manual"

_request_404_streaks = {}
_request_404_streaks_lock = threading.Lock()


def _as_utc_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class ClientRequestContext:
    remote_addr: str
    client_ip_resolved: str
    forwarded_chain: str | None


@dataclass(frozen=True)
class RequestOriginContext:
    scheme: str
    host: str | None


def normalize_trusted_proxy_header(value):
    """Return the proxy header family to trust, or None when the value is not recognised.

    Only one family is ever trusted. A proxy that sets X-Forwarded-* but passes a client's own
    RFC 7239 `Forwarded` header through unchanged (the default for most Nginx setups) would
    otherwise let any client choose its own IP, host and scheme.
    """
    normalized = str(value if value is not None else DEFAULT_TRUSTED_PROXY_HEADER).strip().lower()
    if not normalized:
        normalized = DEFAULT_TRUSTED_PROXY_HEADER
    return normalized if normalized in TRUSTED_PROXY_HEADER_CHOICES else None


def _resolve_trusted_proxy_header(value):
    return normalize_trusted_proxy_header(value) or DEFAULT_TRUSTED_PROXY_HEADER


def resolve_console_log_ip(
    *,
    remote_addr,
    forwarded_header,
    x_forwarded_for_header,
    trusted_proxy_cidrs,
    trusted_proxy_hops,
    trusted_proxy_header=DEFAULT_TRUSTED_PROXY_HEADER,
):
    context = resolve_client_request_context(
        remote_addr=remote_addr,
        forwarded_header=forwarded_header,
        x_forwarded_for_header=x_forwarded_for_header,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        trusted_proxy_hops=trusted_proxy_hops,
        trusted_proxy_header=trusted_proxy_header,
    )
    return context.client_ip_resolved or context.remote_addr


def _parse_ip_candidate(value):
    candidate = str(value or "").strip().strip('"')
    if not candidate or candidate.lower() == "unknown" or candidate.startswith("_"):
        return None

    if candidate.startswith("["):
        closing_index = candidate.find("]")
        if closing_index > 0:
            candidate = candidate[1:closing_index]
    elif candidate.count(":") == 1 and "." in candidate:
        host_candidate, _, _port_candidate = candidate.rpartition(":")
        if host_candidate:
            candidate = host_candidate

    try:
        return str(ip_address(candidate))
    except ValueError:
        return None


def normalize_ip_address(value):
    return _parse_ip_candidate(value)


def normalize_host(value):
    text = str(value or "").strip()
    if not text:
        return None

    parsed = urlsplit(f"//{text}")
    hostname = (parsed.hostname or "").strip().rstrip(".").lower()
    return hostname or None


def _is_request_from_trusted_proxy(*, remote_addr, trusted_proxy_cidrs, trusted_proxy_hops):
    remote_ip = _parse_ip_candidate(remote_addr) or "unknown"
    trusted_proxy_list = [cidr for cidr in (trusted_proxy_cidrs or []) if str(cidr).strip()]
    has_trusted_proxy_cidrs = bool(trusted_proxy_list)
    use_trusted_proxy_hops = bool(trusted_proxy_hops and trusted_proxy_hops > 0 and not has_trusted_proxy_cidrs)

    if has_trusted_proxy_cidrs:
        return _is_trusted_proxy_ip(remote_ip, trusted_proxy_list)
    return use_trusted_proxy_hops


def _parse_forwarded_header_param(header_value, param_name):
    """Return the right-most value of `param_name`: the one added by the nearest proxy."""
    if not header_value or not param_name:
        return None

    target_key = str(param_name).strip().lower()
    for hop in reversed(str(header_value).split(",")):
        for pair in hop.split(";"):
            key, separator, raw_value = pair.partition("=")
            if separator != "=" or key.strip().lower() != target_key:
                continue
            candidate = str(raw_value or "").strip().strip('"')
            if candidate:
                return candidate
    return None


def _parse_scheme_candidate(value):
    candidate = str(value or "").strip().lower()
    if candidate in {"http", "https"}:
        return candidate
    return None


def _last_list_item(value):
    return str(value).rsplit(",", 1)[-1]


def _parse_x_forwarded_proto(value):
    if not value:
        return None
    return _parse_scheme_candidate(_last_list_item(value))


def _parse_x_forwarded_host(value):
    if not value:
        return None
    return normalize_host(_last_list_item(value))


def resolve_request_origin_context(
    *,
    remote_addr,
    forwarded_header,
    x_forwarded_proto_header,
    x_forwarded_host_header,
    trusted_proxy_cidrs,
    trusted_proxy_hops,
    current_scheme,
    current_host,
    trusted_proxy_header=DEFAULT_TRUSTED_PROXY_HEADER,
):
    resolved_scheme = _parse_scheme_candidate(current_scheme) or "http"
    resolved_host = normalize_host(current_host)

    if not _is_request_from_trusted_proxy(
        remote_addr=remote_addr,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        trusted_proxy_hops=trusted_proxy_hops,
    ):
        return RequestOriginContext(scheme=resolved_scheme, host=resolved_host)

    if _resolve_trusted_proxy_header(trusted_proxy_header) == TRUSTED_PROXY_HEADER_FORWARDED:
        forwarded_proto = _parse_scheme_candidate(_parse_forwarded_header_param(forwarded_header, "proto"))
        forwarded_host = normalize_host(_parse_forwarded_header_param(forwarded_header, "host"))
    else:
        forwarded_proto = _parse_x_forwarded_proto(x_forwarded_proto_header)
        forwarded_host = _parse_x_forwarded_host(x_forwarded_host_header)

    return RequestOriginContext(scheme=forwarded_proto or resolved_scheme, host=forwarded_host or resolved_host)


def _parse_forwarded_header_ip_chain(header_value):
    if not header_value:
        return []

    ips = []
    for hop in str(header_value).split(","):
        for pair in hop.split(";"):
            key, separator, raw_value = pair.partition("=")
            if separator != "=" or key.strip().lower() != "for":
                continue
            parsed_ip = _parse_ip_candidate(raw_value)
            if parsed_ip:
                ips.append(parsed_ip)
    return ips


def _parse_x_forwarded_for_ip_chain(header_value):
    if not header_value:
        return []
    ips = []
    for item in str(header_value).split(","):
        parsed_ip = _parse_ip_candidate(item)
        if parsed_ip:
            ips.append(parsed_ip)
    return ips


def _is_trusted_proxy_ip(ip_text, trusted_cidrs):
    if not ip_text:
        return False
    try:
        parsed_ip = ip_address(ip_text)
    except ValueError:
        return False

    for cidr in trusted_cidrs:
        try:
            if parsed_ip in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def is_ip_in_cidrs(ip_text, cidrs):
    normalized_ip = normalize_ip_address(ip_text)
    if not normalized_ip:
        return False
    return _is_trusted_proxy_ip(normalized_ip, cidrs or [])


def is_direct_connection_allowed(remote_addr, trusted_proxy_cidrs):
    """Proxy-only policy: allow a socket peer only if it is a trusted proxy or loopback.

    With no trusted proxy CIDRs configured there is no proxy to enforce, so everything is allowed.
    """
    trusted_proxy_list = [cidr for cidr in (trusted_proxy_cidrs or []) if str(cidr).strip()]
    if not trusted_proxy_list:
        return True
    remote_ip = _parse_ip_candidate(remote_addr)
    if remote_ip is None:
        return False
    if ip_address(remote_ip).is_loopback:
        return True
    return _is_trusted_proxy_ip(remote_ip, trusted_proxy_list)


def resolve_client_request_context(
    *,
    remote_addr,
    forwarded_header,
    x_forwarded_for_header,
    trusted_proxy_cidrs,
    trusted_proxy_hops,
    trusted_proxy_header=DEFAULT_TRUSTED_PROXY_HEADER,
):
    remote_ip = _parse_ip_candidate(remote_addr) or "unknown"
    trusted_proxy_list = [cidr for cidr in (trusted_proxy_cidrs or []) if str(cidr).strip()]
    has_trusted_proxy_cidrs = bool(trusted_proxy_list)
    use_trusted_proxy_hops = bool(trusted_proxy_hops and trusted_proxy_hops > 0 and not has_trusted_proxy_cidrs)

    is_trusted_proxy = _is_request_from_trusted_proxy(
        remote_addr=remote_addr,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        trusted_proxy_hops=trusted_proxy_hops,
    )

    if not is_trusted_proxy:
        return ClientRequestContext(
            remote_addr=remote_ip,
            client_ip_resolved=remote_ip,
            forwarded_chain=None,
        )

    if _resolve_trusted_proxy_header(trusted_proxy_header) == TRUSTED_PROXY_HEADER_FORWARDED:
        forwarded_chain_ips = _parse_forwarded_header_ip_chain(forwarded_header)
    else:
        forwarded_chain_ips = _parse_x_forwarded_for_ip_chain(x_forwarded_for_header)

    if not forwarded_chain_ips:
        return ClientRequestContext(
            remote_addr=remote_ip,
            client_ip_resolved=remote_ip,
            forwarded_chain=None,
        )

    if use_trusted_proxy_hops:
        if len(forwarded_chain_ips) >= trusted_proxy_hops:
            resolved_ip = forwarded_chain_ips[-trusted_proxy_hops]
        else:
            resolved_ip = remote_ip
        return ClientRequestContext(
            remote_addr=remote_ip,
            client_ip_resolved=resolved_ip,
            forwarded_chain=", ".join(forwarded_chain_ips),
        )

    full_chain = forwarded_chain_ips + [remote_ip]
    resolved_ip = remote_ip
    for candidate in reversed(full_chain):
        if not _is_trusted_proxy_ip(candidate, trusted_proxy_list):
            resolved_ip = candidate
            break

    return ClientRequestContext(
        remote_addr=remote_ip,
        client_ip_resolved=resolved_ip,
        forwarded_chain=", ".join(forwarded_chain_ips),
    )


# Proxy header probe: the admin UI sends these marker values; the analysis reports what the proxy
# did with each header before it reached the app. 192.0.2.0/24 is a documentation-only range.
PROXY_PROBE_REQUEST_HEADER = "X-Jigsaurium-Proxy-Probe"
PROXY_PROBE_FORWARDED_FOR = "192.0.2.1"
PROXY_PROBE_X_FORWARDED_FOR = "192.0.2.2"
PROXY_PROBE_PROTO = "http"
PROXY_PROBE_HOST_PORT_SUFFIX = ":1"

PROXY_HEADER_PASSED_THROUGH = "passed_through"
PROXY_HEADER_APPENDED = "appended"
PROXY_HEADER_OVERWRITTEN = "overwritten"
PROXY_HEADER_STRIPPED = "stripped"
PROXY_HEADER_PROXY_SET_SAFE = {PROXY_HEADER_APPENDED, PROXY_HEADER_OVERWRITTEN}


def _classify_probed_list_header(value, marker_ip, parse_chain):
    if not value:
        return PROXY_HEADER_STRIPPED
    chain = parse_chain(value)
    if marker_ip not in chain:
        return PROXY_HEADER_OVERWRITTEN
    if chain[-1] != marker_ip:
        return PROXY_HEADER_APPENDED
    return PROXY_HEADER_PASSED_THROUGH


def _classify_probed_single_header(value, marker):
    text = str(value or "").strip()
    if not text:
        return PROXY_HEADER_STRIPPED
    items = [item.strip() for item in text.split(",")]
    if marker not in items:
        return PROXY_HEADER_OVERWRITTEN
    if items[-1] != marker:
        return PROXY_HEADER_APPENDED
    return PROXY_HEADER_PASSED_THROUGH


def analyse_proxy_header_probe(
    *,
    remote_addr,
    headers,
    trusted_proxy_cidrs,
    trusted_proxy_hops,
    trusted_proxy_header,
    probe_host,
):
    """Report how the proxy treated client-supplied forwarding headers and recommend a setting.

    `headers` maps header names to received values. `probe_host` is the host the browser was on;
    the probe sends it with a `:1` port so a passed-through host value is recognisable while still
    normalising to the canonical host.
    """
    trusted_proxy_header = _resolve_trusted_proxy_header(trusted_proxy_header)
    remote_ip = _parse_ip_candidate(remote_addr) or "unknown"
    remote_is_trusted_proxy = _is_request_from_trusted_proxy(
        remote_addr=remote_addr,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        trusted_proxy_hops=trusted_proxy_hops,
    )
    probe_sent = str(headers.get(PROXY_PROBE_REQUEST_HEADER) or "").strip() == "1"
    probe_host_value = f"{str(probe_host or '').strip()}{PROXY_PROBE_HOST_PORT_SUFFIX}"

    findings = {}
    if probe_sent:
        findings = {
            "forwarded": _classify_probed_list_header(
                headers.get("Forwarded"), PROXY_PROBE_FORWARDED_FOR, _parse_forwarded_header_ip_chain
            ),
            "x_forwarded_for": _classify_probed_list_header(
                headers.get("X-Forwarded-For"), PROXY_PROBE_X_FORWARDED_FOR, _parse_x_forwarded_for_ip_chain
            ),
            "x_forwarded_proto": _classify_probed_single_header(headers.get("X-Forwarded-Proto"), PROXY_PROBE_PROTO),
            "x_forwarded_host": _classify_probed_single_header(headers.get("X-Forwarded-Host"), probe_host_value),
        }

    messages = []
    recommended = None
    verdict = "unknown"
    if not remote_is_trusted_proxy:
        verdict = "warning"
        messages.append(
            f"The request reached the app from {remote_ip}, which is not in TRUSTED_PROXY_CIDRS, so all "
            "forwarding headers are ignored and every client appears as that address. If that is your proxy, "
            "add it to TRUSTED_PROXY_CIDRS (and to TRUSTED_CLIENT_CIDRS so it can never be auto-blocked)."
        )
    if probe_sent:
        xff_safe = findings["x_forwarded_for"] in PROXY_HEADER_PROXY_SET_SAFE
        forwarded_safe = findings["forwarded"] in PROXY_HEADER_PROXY_SET_SAFE
        if xff_safe:
            recommended = TRUSTED_PROXY_HEADER_X_FORWARDED
        elif forwarded_safe:
            recommended = TRUSTED_PROXY_HEADER_FORWARDED

        if recommended is None:
            verdict = "unsafe"
            messages.append(
                "The proxy does not set a client-IP header the app can trust: client-supplied values arrive "
                "unchanged or nothing arrives. Login throttling and IP blocks then key on a value the client "
                "chooses (or on the proxy address)."
            )
        else:
            if verdict == "unknown":
                verdict = "ok"
            if recommended != trusted_proxy_header:
                verdict = "unsafe"
                messages.append(
                    f"TRUSTED_PROXY_HEADER is '{trusted_proxy_header}', but the proxy does not overwrite that "
                    f"header family, so clients can choose their own IP. Set TRUSTED_PROXY_HEADER={recommended}."
                )

        if findings["forwarded"] == PROXY_HEADER_PASSED_THROUGH:
            messages.append(
                "The proxy passes the client's own Forwarded header through unchanged; it must not be trusted."
            )
        if trusted_proxy_header == TRUSTED_PROXY_HEADER_X_FORWARDED:
            header_labels = {"x_forwarded_host": "X-Forwarded-Host", "x_forwarded_proto": "X-Forwarded-Proto"}
            spoofable = [
                label for name, label in header_labels.items() if findings[name] == PROXY_HEADER_PASSED_THROUGH
            ]
            if spoofable:
                if verdict == "ok":
                    verdict = "warning"
                messages.append(
                    f"{' and '.join(spoofable)} pass through from the client, so clients can choose the host and "
                    "scheme the app sees. Impact is limited (canonical-host check and HSTS), but ask for the proxy "
                    "to set them."
                )

    context = resolve_client_request_context(
        remote_addr=remote_addr,
        forwarded_header=headers.get("Forwarded"),
        x_forwarded_for_header=headers.get("X-Forwarded-For"),
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        trusted_proxy_hops=trusted_proxy_hops,
        trusted_proxy_header=trusted_proxy_header,
    )
    return {
        "probe_sent": probe_sent,
        "remote_addr": remote_ip,
        "remote_is_trusted_proxy": remote_is_trusted_proxy,
        "config": {
            "trusted_proxy_header": trusted_proxy_header,
            "trusted_proxy_cidrs": list(trusted_proxy_cidrs or []),
            "trusted_proxy_hops": trusted_proxy_hops,
        },
        "received": {
            "host": headers.get("Host"),
            "forwarded": headers.get("Forwarded"),
            "x_forwarded_for": headers.get("X-Forwarded-For"),
            "x_forwarded_proto": headers.get("X-Forwarded-Proto"),
            "x_forwarded_host": headers.get("X-Forwarded-Host"),
            "x_real_ip": headers.get("X-Real-IP"),
        },
        "resolved_client_ip": context.client_ip_resolved,
        "findings": findings,
        "recommended_trusted_proxy_header": recommended,
        "verdict": verdict,
        "messages": messages,
    }


def get_request_ban_retry_after_seconds(db_session, client_ip, exempt_cidrs=None, now=None):
    normalized_ip = normalize_ip_address(client_ip)
    if not normalized_ip:
        return None
    if is_ip_in_cidrs(normalized_ip, exempt_cidrs):
        return None

    current_time = now or datetime.now(timezone.utc)
    block = db_session.execute(select(BlockedIp).where(BlockedIp.ip_address == normalized_ip)).scalar_one_or_none()
    if block is None or block.blocked_until is None:
        return None

    blocked_until = _as_utc_datetime(block.blocked_until)
    if blocked_until <= current_time:
        return None

    return max(1, int((blocked_until - current_time).total_seconds()))


def record_request_outcome(client_ip, status_code, exempt_cidrs=None):
    normalized_ip = normalize_ip_address(client_ip)
    if not normalized_ip:
        return False
    if is_ip_in_cidrs(normalized_ip, exempt_cidrs):
        with _request_404_streaks_lock:
            _request_404_streaks.pop(normalized_ip, None)
        return False

    with _request_404_streaks_lock:
        if int(status_code or 0) == 404:
            new_count = int(_request_404_streaks.get(normalized_ip, 0) or 0) + 1
            if new_count >= REQUEST_BAN_TRIGGER_404_STREAK:
                _request_404_streaks.pop(normalized_ip, None)
                return True
            _request_404_streaks[normalized_ip] = new_count
            return False

        _request_404_streaks.pop(normalized_ip, None)
        return False


def upsert_blocked_ip(
    db_session,
    *,
    ip_address,
    blocked_until,
    block_source,
    block_reason=None,
    notes=None,
    created_by_user_id=None,
    add_hit=False,
    exempt_cidrs=None,
):
    normalized_ip = normalize_ip_address(ip_address)
    if not normalized_ip:
        raise ValueError("Invalid IP address.")
    if is_ip_in_cidrs(normalized_ip, exempt_cidrs):
        raise ValueError("Trusted internal IP addresses cannot be blocked.")

    now = datetime.now(timezone.utc)
    existing = db_session.execute(select(BlockedIp).where(BlockedIp.ip_address == normalized_ip)).scalar_one_or_none()
    resolved_blocked_until = _as_utc_datetime(blocked_until)
    if resolved_blocked_until is None:
        raise ValueError("Blocked-until timestamp is required.")
    if existing is None:
        hit_count = 1 if add_hit else 0
        block = BlockedIp(
            ip_address=normalized_ip,
            blocked_until=resolved_blocked_until,
            block_source=str(block_source or AUTO_BLOCK_SOURCE),
            block_reason=block_reason,
            notes=notes,
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
            hit_count=hit_count,
        )
        db_session.add(block)
        db_session.flush()
        return block

    existing_blocked_until = _as_utc_datetime(existing.blocked_until) or resolved_blocked_until
    existing.blocked_until = max(existing_blocked_until, resolved_blocked_until)
    existing.block_source = str(block_source or existing.block_source or AUTO_BLOCK_SOURCE)
    existing.block_reason = block_reason
    existing.notes = notes
    existing.created_by_user_id = created_by_user_id
    if add_hit:
        existing.hit_count = int(existing.hit_count or 0) + 1
    existing.updated_at = now
    db_session.flush()
    return existing


def build_auto_blocked_until(now=None):
    current_time = now or datetime.now(timezone.utc)
    return current_time + timedelta(seconds=REQUEST_BAN_DURATION_SECONDS)


def reset_request_security_state():
    with _request_404_streaks_lock:
        _request_404_streaks.clear()
