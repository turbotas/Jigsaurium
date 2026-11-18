from collections.abc import Mapping
import os
import sys

from werkzeug import serving
from werkzeug.serving import WSGIRequestHandler, _log

from app.request_security import resolve_console_log_ip


# Set by run.py when it starts the dev server with auto-reload; not a setting to configure.
DEV_RELOADER_ENV = "JIGSAURIUM_DEV_RELOADER"


def is_reloader_watcher_process(argv=None, environ=None):
    """Whether this is the dev auto-reloader's file-watching process.

    With auto-reload, Werkzeug keeps one process watching the source files and runs the app in a
    child process that it restarts after each change. Only the child serves requests, and Werkzeug
    marks it with WERKZEUG_RUN_MAIN=true. The watcher still imports run.py and builds the app, so
    heavy start-up work there (loading the image model) is wasted.
    """
    argv = sys.argv if argv is None else argv
    environ = os.environ if environ is None else environ
    if environ.get("WERKZEUG_RUN_MAIN") == "true":
        return False
    if environ.get(DEV_RELOADER_ENV) == "1":  # python run.py (run.sh)
        return True
    # flask --app run:app run --reload (run.bat, scripts/run_simple.sh)
    return "run" in argv and "--reload" in argv[argv.index("run") + 1 :]


def _extract_flask_config(wsgi_app):
    current = wsgi_app
    for _ in range(8):
        if current is None:
            break
        config = getattr(current, "config", None)
        if isinstance(config, Mapping):
            return config
        current = getattr(current, "app", None)
    return {}


class ForwardedAwareWSGIRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        resolved_remote_addr = _resolve_remote_addr_for_log(self)

        # IPv6 scoped addresses contain "%", which breaks %-formatted log strings.
        safe_remote_addr = str(resolved_remote_addr).replace("%", "%%")
        _log(
            type,
            f"{safe_remote_addr} - - [{self.log_date_time_string()}] {message}\n",
            *args,
        )


def _resolve_remote_addr_for_log(handler):
    resolved_remote_addr = handler.address_string()

    try:
        environ = getattr(handler, "environ", {}) or {}
        config = _extract_flask_config(getattr(handler.server, "app", None))
        resolved_remote_addr = resolve_console_log_ip(
            remote_addr=environ.get("REMOTE_ADDR", resolved_remote_addr),
            forwarded_header=environ.get("HTTP_FORWARDED"),
            x_forwarded_for_header=environ.get("HTTP_X_FORWARDED_FOR"),
            trusted_proxy_cidrs=config.get("TRUSTED_PROXY_CIDRS", []),
            trusted_proxy_hops=config.get("TRUSTED_PROXY_HOPS"),
            trusted_proxy_header=config.get("TRUSTED_PROXY_HEADER"),
        )
    except Exception:
        resolved_remote_addr = handler.address_string()

    return resolved_remote_addr


def install_forwarded_aware_werkzeug_logging():
    if getattr(WSGIRequestHandler, "_jigsaurium_forwarded_log_patch", False):
        return

    def _patched_log(self, type, message, *args):
        resolved_remote_addr = _resolve_remote_addr_for_log(self)

        # IPv6 scoped addresses contain "%", which breaks %-formatted log strings.
        safe_remote_addr = str(resolved_remote_addr).replace("%", "%%")
        _log(
            type,
            f"{safe_remote_addr} - - [{self.log_date_time_string()}] {message}\n",
            *args,
        )

    WSGIRequestHandler.log = _patched_log
    WSGIRequestHandler._jigsaurium_forwarded_log_patch = True
    serving.WSGIRequestHandler.log = _patched_log
