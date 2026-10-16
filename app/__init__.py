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
    app.config.setdefault("AI_ENABLED", False)
    app.config.setdefault("AI_API_KEY", "")
    app.config.setdefault("AI_ENDPOINT_URL", "")
    app.config.setdefault("AI_MODEL", "")
    app.config.setdefault("AI_TIMEOUT_SECONDS", 60)
    app.config.setdefault("AI_DAILY_BUDGET_USD", None)
    app.config.setdefault("BULK_AI_CREATE_INLINE", bool(app.config.get("TESTING", False)))
    app.config.setdefault("IMAGE_EMBEDDINGS_ENABLED", False)
    app.config.setdefault("IMAGE_EMBEDDING_MODEL_NAME", "openai/clip-vit-base-patch32")
    app.config.setdefault("IMAGE_EMBEDDING_MODEL_REVISION", "main")
    app.config.setdefault("IMAGE_EMBEDDINGS_INLINE", bool(app.config.get("TESTING", False)))
    app.config.setdefault("IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK", bool(app.config.get("TESTING", False)))
    app.config.setdefault("IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES", ["box", "reference"])

    @app.before_request
    def set_request_id():
        g.request_id = f"req_{uuid4().hex[:12]}"

    from app.routes import main_bp
    from app.api.v1 import api_v1_bp
    from app.api.v1.routes import start_bulk_ai_create_worker
    from app import models  # noqa: F401

    app.register_blueprint(main_bp)
    app.register_blueprint(api_v1_bp)
    init_db(app)
    start_bulk_ai_create_worker(app)
    return app
