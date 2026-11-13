from app import create_app
from app.dev_server import ForwardedAwareWSGIRequestHandler
from app.govuk import check_govuk_version_freshness

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


app = create_app()
check_govuk_version_freshness(app)


if __name__ == "__main__":
    # Never debug mode: every environment, dev included, is reachable through the public proxy, and
    # debug mode would expose tracebacks and the Werkzeug debugger. Dev keeps auto-reload.
    app.run(
        debug=False,
        use_reloader=app.config["APP_ENV"] == "dev",
        request_handler=ForwardedAwareWSGIRequestHandler,
    )
