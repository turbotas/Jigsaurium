from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, g, request
from werkzeug.exceptions import RequestEntityTooLarge

from app.db import get_session, init_db
from app.dev_server import install_forwarded_aware_werkzeug_logging
from app.request_security import (
    AUTO_BLOCK_SOURCE,
    build_auto_blocked_until,
    get_request_ban_retry_after_seconds,
    record_request_outcome,
    resolve_client_request_context,
    reset_request_security_state,
    upsert_blocked_ip,
)


def create_app(config_class="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    install_forwarded_aware_werkzeug_logging()

    app.config.setdefault("APP_ENV", "dev")
    app.config.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    app.config.setdefault("LOG_LEVEL", "INFO")
    app.config.setdefault("CANONICAL_HOST", "localhost")
    app.config.setdefault("TRUSTED_PROXY_CIDRS", [])
    app.config.setdefault("TRUSTED_PROXY_HOPS", None)
    app.config.setdefault("TRUSTED_CLIENT_CIDRS", [])
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
    app.config.setdefault("MAX_CONTENT_LENGTH", 32 * 1024 * 1024)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    @app.before_request
    def set_request_id():
        g.request_id = f"req_{uuid4().hex[:12]}"
        client_context = resolve_client_request_context(
            remote_addr=request.remote_addr,
            forwarded_header=request.headers.get("Forwarded"),
            x_forwarded_for_header=request.headers.get("X-Forwarded-For"),
            trusted_proxy_cidrs=app.config.get("TRUSTED_PROXY_CIDRS", []),
            trusted_proxy_hops=app.config.get("TRUSTED_PROXY_HOPS"),
        )
        g.remote_addr = client_context.remote_addr
        g.client_ip_resolved = client_context.client_ip_resolved
        g.forwarded_chain = client_context.forwarded_chain

        db_session = get_session()
        retry_after_seconds = get_request_ban_retry_after_seconds(
            db_session,
            g.client_ip_resolved,
            exempt_cidrs=app.config.get("TRUSTED_CLIENT_CIDRS", []),
        )
        if retry_after_seconds is not None:
            if request.path.startswith("/api/v1"):
                payload = {
                    "error": {
                        "code": "too_many_requests",
                        "message": "Request blocked due to suspicious repeated not-found probing.",
                        "details": [],
                    },
                    "meta": {"request_id": g.request_id},
                }
                response = app.response_class(
                    response=app.json.dumps(payload),
                    status=429,
                    mimetype="application/json",
                )
            else:
                response = app.response_class(
                    response="Request blocked due to suspicious repeated not-found probing.",
                    status=429,
                    mimetype="text/plain",
                )

            response.headers["Retry-After"] = str(retry_after_seconds)
            return response

    @app.after_request
    def apply_security_headers(response):
        was_ban_triggered = record_request_outcome(
            getattr(g, "client_ip_resolved", request.remote_addr),
            response.status_code,
            exempt_cidrs=app.config.get("TRUSTED_CLIENT_CIDRS", []),
        )
        if was_ban_triggered:
            db_session = get_session()
            try:
                upsert_blocked_ip(
                    db_session,
                    ip_address=getattr(g, "client_ip_resolved", request.remote_addr),
                    blocked_until=build_auto_blocked_until(datetime.now(timezone.utc)),
                    block_source=AUTO_BLOCK_SOURCE,
                    block_reason="5 consecutive 404 responses",
                    created_by_user_id=None,
                    add_hit=True,
                    exempt_cidrs=app.config.get("TRUSTED_CLIENT_CIDRS", []),
                )
                db_session.commit()
            except Exception:
                db_session.rollback()

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';",
        )
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_error):
        if request.path.startswith("/api/v1"):
            request_id = getattr(g, "request_id", f"req_{uuid4().hex[:12]}")
            payload = {
                "error": {
                    "code": "payload_too_large",
                    "message": "Request payload exceeds the maximum allowed size.",
                    "details": [],
                },
                "meta": {"request_id": request_id},
            }
            return payload, 413
        return "Request payload exceeds the maximum allowed size.", 413

    from app.routes import main_bp
    from app.api.v1 import api_v1_bp
    from app.api.v1.routes import reset_runtime_security_state, start_bulk_ai_create_worker
    from app import models  # noqa: F401

    app.register_blueprint(main_bp)
    app.register_blueprint(api_v1_bp)
    init_db(app)
    reset_runtime_security_state()
    reset_request_security_state()
    start_bulk_ai_create_worker(app)
    return app
