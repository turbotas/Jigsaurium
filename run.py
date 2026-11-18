import os

from werkzeug.serving import is_running_from_reloader

from app import create_app
from app.dev_server import DEV_RELOADER_ENV, ForwardedAwareWSGIRequestHandler
from app.govuk import check_govuk_version_freshness

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


# Dev keeps auto-reload. Mark the reloader's watcher process before the app is built, so it skips
# start-up work only the serving process needs (see is_reloader_watcher_process).
use_reloader = __name__ == "__main__" and os.getenv("APP_ENV", "dev") == "dev"
if use_reloader and not is_running_from_reloader():
    os.environ[DEV_RELOADER_ENV] = "1"

app = create_app()
check_govuk_version_freshness(app)


if __name__ == "__main__":
    # Never debug mode: every environment, dev included, is reachable through the public proxy, and
    # debug mode would expose tracebacks and the Werkzeug debugger. Dev keeps auto-reload.
    app.run(
        debug=False,
        use_reloader=use_reloader,
        request_handler=ForwardedAwareWSGIRequestHandler,
    )
