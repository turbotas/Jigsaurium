"""Gunicorn settings for the container image (production WSGI server).

One worker process with threads: background jobs (bulk AI create, embedding backfill), the
embedding model and the 404-streak tracker live in process memory, so they must not be split
across several worker processes. The app is created inside the worker (no preload), so the
background threads start after the fork.

Every value can be overridden with an environment variable of the same name.
"""

import os


def _int_env(name, default):
    raw = os.getenv(name, "")
    try:
        return int(raw) if raw.strip() else default
    except ValueError as error:
        raise ValueError(f"Invalid {name}: expected integer, got {raw!r}") from error


bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = 1
worker_class = "gthread"
threads = _int_env("GUNICORN_THREADS", 8)

# Kill a worker that stops responding (AI calls are bounded by AI_TIMEOUT_SECONDS, default 60).
timeout = _int_env("GUNICORN_TIMEOUT", 180)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
# Idle keep-alive connections are closed quickly so held-open sockets cannot pile up.
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

# Bound request line and header sizes (protects against oversized-header abuse).
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Restart the worker periodically to cap any slow memory growth.
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 5000)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 500)

# forwarded_allow_ips is left at gunicorn's default (loopback only), so gunicorn does not rewrite
# the scheme from forwarding headers sent by the proxy. The app resolves client IP, host and
# scheme itself from the TRUSTED_PROXY_* settings.

# Access log to stdout. %(h)s is the socket peer (the proxy); the forwarded value is shown as
# received and is only trustworthy when the proxy overwrites it.
accesslog = "-"
access_log_format = '%(h)s fwd="%({x-forwarded-for}i)s" "%(r)s" %(s)s %(b)s %(M)sms'
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
