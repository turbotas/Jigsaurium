import json
from secrets import token_urlsafe
from functools import wraps

from flask import Blueprint, current_app, g, request, session
from sqlalchemy import select

from app.db import get_session
from app.models import AuditEvent, Jigsaw, Role, User, UserRole
from app.models.jigsaw import JigsawStatus


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _success_response(data, status_code=200):
    return {"data": data, "meta": {"request_id": g.request_id}}, status_code


def _error_response(code, message, status_code, details=None):
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
        "meta": {"request_id": g.request_id},
    }
    return payload, status_code


def _parse_json_object():
    payload = request.get_json(silent=True)
    if payload is None:
        return None, _error_response("bad_request", "Expected JSON request body.", 400)
    if not isinstance(payload, dict):
        return None, _error_response("bad_request", "JSON body must be an object.", 400)
    return payload, None


def _serialize_user(user, roles):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "roles": sorted(roles),
    }


def _serialize_jigsaw(jigsaw):
    return {
        "id": jigsaw.id,
        "title": jigsaw.title,
        "piece_count": jigsaw.piece_count,
        "condition": jigsaw.condition,
        "status": jigsaw.status.value,
        "tags": jigsaw.tags,
    }


def _record_audit_event(action, entity_type, entity_id, payload=None):
    db_session = get_session()
    forwarded_chain = request.headers.get("Forwarded") or request.headers.get("X-Forwarded-For")

    audit_event = AuditEvent(
        actor_user_id=getattr(g.current_user, "id", None),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        request_id=g.request_id,
        remote_addr=request.remote_addr,
        client_ip_resolved=request.remote_addr,
        forwarded_chain=forwarded_chain,
        scheme=request.scheme,
        host=request.host,
        payload_json=json.dumps(payload, sort_keys=True) if payload is not None else None,
    )
    db_session.add(audit_event)


def _get_role_names_for_user_id(user_id):
    db_session = get_session()
    return db_session.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    ).scalars().all()


def _load_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    user_id = session.get("user_id")
    if user_id is None:
        g.current_user = None
        g.current_user_roles = []
        return None

    db_session = get_session()
    user = db_session.get(User, user_id)
    if user is None or not user.is_active:
        g.current_user = None
        g.current_user_roles = []
        return None

    role_names = _get_role_names_for_user_id(user.id)

    g.current_user = user
    g.current_user_roles = role_names
    return user


def _validate_csrf_for_request():
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None

    expected_token = session.get("csrf_token")
    provided_token = request.headers.get("X-CSRF-Token")
    if expected_token is None or provided_token != expected_token:
        return _error_response("forbidden", "CSRF token is missing or invalid.", 403)

    return None


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = _load_current_user()
        if user is None:
            return _error_response(
                "authentication_required",
                "Authentication is required for this endpoint.",
                401,
            )

        csrf_error = _validate_csrf_for_request()
        if csrf_error is not None:
            return csrf_error

        return view_func(*args, **kwargs)

    return wrapper


def require_role(required_role):
    def decorator(view_func):
        @wraps(view_func)
        @require_auth
        def wrapper(*args, **kwargs):
            if required_role not in g.current_user_roles:
                return _error_response(
                    "forbidden",
                    "You do not have permission to access this resource.",
                    403,
                )
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def _validate_roles(role_names):
    if not isinstance(role_names, list) or len(role_names) == 0:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "roles", "issue": "must be a non-empty list"}],
        )

    normalized_roles = []
    for role_name in role_names:
        if not isinstance(role_name, str) or not role_name.strip():
            return None, _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "roles", "issue": "all roles must be non-empty strings"}],
            )
        normalized_roles.append(role_name.strip())

    db_session = get_session()
    roles = db_session.execute(select(Role).where(Role.name.in_(set(normalized_roles)))).scalars().all()
    roles_by_name = {role.name: role for role in roles}

    unknown_roles = sorted({role for role in normalized_roles if role not in roles_by_name})
    if unknown_roles:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "roles", "issue": f"unknown roles: {', '.join(unknown_roles)}"}],
        )

    return [roles_by_name[name] for name in normalized_roles], None


def _parse_jigsaw_status(raw_status):
    if not isinstance(raw_status, str):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "status", "issue": "must be a string"}],
        )

    try:
        status = JigsawStatus(raw_status.strip())
    except ValueError:
        valid_statuses = ", ".join(item.value for item in JigsawStatus)
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "status", "issue": f"must be one of: {valid_statuses}"}],
        )
    return status, None


@api_v1_bp.get("/health")
def health_check():
    payload = {
        "status": "ok",
        "environment": current_app.config["APP_ENV"],
    }
    return _success_response(payload)


@api_v1_bp.post("/auth/login")
def auth_login():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": "must be a non-empty string"}],
        )

    password = payload.get("password")
    if not isinstance(password, str) or not password:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "password", "issue": "must be a non-empty string"}],
        )

    db_session = get_session()
    user = db_session.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    if user is None or not user.is_active or not user.check_password(password):
        return _error_response("authentication_failed", "Invalid credentials.", 401)

    role_names = _get_role_names_for_user_id(user.id)
    csrf_token = token_urlsafe(24)

    session["user_id"] = user.id
    session["csrf_token"] = csrf_token
    g.current_user = user
    g.current_user_roles = role_names

    _record_audit_event(
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        payload={"roles": sorted(role_names)},
    )
    db_session.commit()

    return _success_response(
        {
            "user": _serialize_user(user, role_names),
            "csrf_token": csrf_token,
        }
    )


@api_v1_bp.get("/auth/me")
@require_auth
def auth_me():
    return _success_response({"user": _serialize_user(g.current_user, g.current_user_roles)})


@api_v1_bp.post("/auth/logout")
@require_auth
def auth_logout():
    db_session = get_session()
    _record_audit_event(
        action="auth.logout",
        entity_type="user",
        entity_id=g.current_user.id,
    )
    db_session.commit()

    session.pop("user_id", None)
    session.pop("csrf_token", None)

    g.current_user = None
    g.current_user_roles = []
    return _success_response({"logged_out": True})


@api_v1_bp.get("/roles")
@require_role("administrator")
def list_roles():
    db_session = get_session()
    roles = db_session.execute(select(Role).order_by(Role.name)).scalars().all()
    payload = [{"id": role.id, "name": role.name, "description": role.description} for role in roles]
    return _success_response(payload)


@api_v1_bp.get("/users")
@require_role("administrator")
def list_users():
    db_session = get_session()
    users = db_session.execute(select(User).order_by(User.id)).scalars().all()

    role_rows = db_session.execute(
        select(UserRole.user_id, Role.name).join(Role, Role.id == UserRole.role_id).order_by(UserRole.user_id, Role.name)
    ).all()

    roles_by_user_id = {}
    for user_id, role_name in role_rows:
        roles_by_user_id.setdefault(user_id, []).append(role_name)

    payload = [_serialize_user(user, roles_by_user_id.get(user.id, [])) for user in users]
    return _success_response(payload)


@api_v1_bp.post("/users")
@require_role("administrator")
def create_user():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": "must be a non-empty string"}],
        )
    email = email.strip().lower()

    display_name = payload.get("display_name")
    if display_name is not None and not isinstance(display_name, str):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "display_name", "issue": "must be a string or null"}],
        )

    is_active = payload.get("is_active", True)
    if not isinstance(is_active, bool):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "is_active", "issue": "must be a boolean"}],
        )

    roles, error = _validate_roles(payload.get("roles"))
    if error is not None:
        return error

    db_session = get_session()
    existing_user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing_user is not None:
        return _error_response("conflict", "A user with this email already exists.", 409)

    user = User(email=email, display_name=display_name, is_active=is_active)
    db_session.add(user)
    db_session.flush()

    for role in roles:
        db_session.add(UserRole(user_id=user.id, role_id=role.id))

    _record_audit_event(
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        payload={"email": user.email, "roles": [role.name for role in roles]},
    )
    db_session.commit()

    return _success_response(_serialize_user(user, [role.name for role in roles]), status_code=201)


@api_v1_bp.patch("/users/<int:user_id>")
@require_role("administrator")
def update_user(user_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    updatable_fields = {"email", "display_name", "is_active", "roles"}
    if not any(field in payload for field in updatable_fields):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "payload", "issue": "must include at least one updatable field"}],
        )

    db_session = get_session()
    user = db_session.get(User, user_id)
    if user is None:
        return _error_response("not_found", "User was not found.", 404)

    if "email" in payload:
        email = payload.get("email")
        if not isinstance(email, str) or not email.strip():
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "email", "issue": "must be a non-empty string"}],
            )
        normalized_email = email.strip().lower()
        existing_user = db_session.execute(select(User).where(User.email == normalized_email, User.id != user.id)).scalar_one_or_none()
        if existing_user is not None:
            return _error_response("conflict", "A user with this email already exists.", 409)
        user.email = normalized_email

    if "display_name" in payload:
        display_name = payload.get("display_name")
        if display_name is not None and not isinstance(display_name, str):
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "display_name", "issue": "must be a string or null"}],
            )
        user.display_name = display_name

    if "is_active" in payload:
        is_active = payload.get("is_active")
        if not isinstance(is_active, bool):
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "is_active", "issue": "must be a boolean"}],
            )
        user.is_active = is_active

    updated_roles = None
    if "roles" in payload:
        roles, error = _validate_roles(payload.get("roles"))
        if error is not None:
            return error

        db_session.execute(UserRole.__table__.delete().where(UserRole.user_id == user.id))
        for role in roles:
            db_session.add(UserRole(user_id=user.id, role_id=role.id))
        updated_roles = [role.name for role in roles]

    if updated_roles is None:
        updated_roles = db_session.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        ).scalars().all()

    _record_audit_event(
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        payload={"updated_fields": sorted(field for field in payload if field in updatable_fields)},
    )
    db_session.commit()

    return _success_response(_serialize_user(user, updated_roles))


@api_v1_bp.get("/jigsaws")
@require_auth
def list_jigsaws():
    db_session = get_session()
    stmt = select(Jigsaw)

    if "administrator" not in g.current_user_roles:
        stmt = stmt.where(Jigsaw.status != JigsawStatus.RETIRED)

    raw_status = request.args.get("status")
    if raw_status:
        status, error = _parse_jigsaw_status(raw_status)
        if error is not None:
            return error
        stmt = stmt.where(Jigsaw.status == status)

    piece_count_min = request.args.get("piece_count_min")
    if piece_count_min is not None:
        try:
            minimum = int(piece_count_min)
        except ValueError:
            return _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "piece_count_min", "issue": "must be an integer"}],
            )
        stmt = stmt.where(Jigsaw.piece_count >= minimum)

    piece_count_max = request.args.get("piece_count_max")
    if piece_count_max is not None:
        try:
            maximum = int(piece_count_max)
        except ValueError:
            return _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "piece_count_max", "issue": "must be an integer"}],
            )
        stmt = stmt.where(Jigsaw.piece_count <= maximum)

    query_text = request.args.get("q")
    if query_text:
        pattern = f"%{query_text.strip()}%"
        stmt = stmt.where(Jigsaw.title.ilike(pattern) | Jigsaw.tags.ilike(pattern))

    jigsaws = db_session.execute(stmt.order_by(Jigsaw.id)).scalars().all()
    payload = [_serialize_jigsaw(jigsaw) for jigsaw in jigsaws]
    return _success_response(payload)


@api_v1_bp.post("/jigsaws")
@require_role("administrator")
def create_jigsaw():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "title", "issue": "must be a non-empty string"}],
        )

    piece_count = payload.get("piece_count")
    if not isinstance(piece_count, int) or piece_count <= 0:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "piece_count", "issue": "must be greater than zero"}],
        )

    raw_status = payload.get("status", JigsawStatus.AVAILABLE.value)
    status, error = _parse_jigsaw_status(raw_status)
    if error is not None:
        return error

    condition = payload.get("condition")
    if condition is not None and not isinstance(condition, str):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "condition", "issue": "must be a string or null"}],
        )

    tags = payload.get("tags")
    if tags is not None and not isinstance(tags, str):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "tags", "issue": "must be a string or null"}],
        )

    db_session = get_session()
    jigsaw = Jigsaw(
        title=title.strip(),
        piece_count=piece_count,
        condition=condition,
        status=status,
        tags=tags,
    )
    db_session.add(jigsaw)
    db_session.flush()

    _record_audit_event(
        action="jigsaw.created",
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={"title": jigsaw.title, "piece_count": piece_count, "status": status.value},
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw(jigsaw), status_code=201)


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>")
@require_auth
def get_jigsaw(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    return _success_response(_serialize_jigsaw(jigsaw))


@api_v1_bp.patch("/jigsaws/<int:jigsaw_id>")
@require_role("administrator")
def update_jigsaw(jigsaw_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    updatable_fields = {"title", "piece_count", "condition", "status", "tags"}
    if not any(field in payload for field in updatable_fields):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "payload", "issue": "must include at least one updatable field"}],
        )

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    original_status = jigsaw.status

    if "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "title", "issue": "must be a non-empty string"}],
            )
        jigsaw.title = title.strip()

    if "piece_count" in payload:
        piece_count = payload.get("piece_count")
        if not isinstance(piece_count, int) or piece_count <= 0:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "piece_count", "issue": "must be greater than zero"}],
            )
        jigsaw.piece_count = piece_count

    if "condition" in payload:
        condition = payload.get("condition")
        if condition is not None and not isinstance(condition, str):
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "condition", "issue": "must be a string or null"}],
            )
        jigsaw.condition = condition

    if "status" in payload:
        status, error = _parse_jigsaw_status(payload.get("status"))
        if error is not None:
            return error
        jigsaw.status = status

    if "tags" in payload:
        tags = payload.get("tags")
        if tags is not None and not isinstance(tags, str):
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "tags", "issue": "must be a string or null"}],
            )
        jigsaw.tags = tags

    action = "jigsaw.updated"
    if jigsaw.status != original_status:
        action = "jigsaw.status_changed"

    _record_audit_event(
        action=action,
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={"updated_fields": sorted(field for field in payload if field in updatable_fields)},
    )
    db_session.commit()
    return _success_response(_serialize_jigsaw(jigsaw))


@api_v1_bp.delete("/jigsaws/<int:jigsaw_id>")
@require_role("administrator")
def retire_jigsaw(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if jigsaw.status != JigsawStatus.RETIRED:
        jigsaw.status = JigsawStatus.RETIRED

    _record_audit_event(
        action="jigsaw.retired",
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={"status": jigsaw.status.value},
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw(jigsaw))
