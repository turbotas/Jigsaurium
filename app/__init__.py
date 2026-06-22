from uuid import uuid4

from flask import Flask, g

from app.db import init_db


def create_app(config_class="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    app.config.setdefault("APP_ENV", "dev")
    app.config.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    app.config.setdefault("LOG_LEVEL", "INFO")
    app.config.setdefault("CANONICAL_HOST", "localhost")
    app.config.setdefault("TRUSTED_PROXY_CIDRS", [])
    app.config.setdefault("TRUSTED_PROXY_HOPS", None)

    @app.before_request
    def set_request_id():
        g.request_id = f"req_{uuid4().hex[:12]}"

    from app.routes import main_bp
    from app.api.v1 import api_v1_bp
    from app import models  # noqa: F401

    app.register_blueprint(main_bp)
    app.register_blueprint(api_v1_bp)
    init_db(app)
    return app
