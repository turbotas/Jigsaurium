import json
import re
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from functools import wraps

from flask import Blueprint, current_app, g, request, session
from sqlalchemy import select

from app.db import get_session
from app.models import AuditEvent, Jigsaw, Loan, Role, User, UserRole
from app.models.jigsaw import JigsawStatus
from app.models.loan import LoanStatus


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
USER_EMAIL_MAX_LENGTH = 255
DISPLAY_NAME_MAX_LENGTH = 255
PASSWORD_MAX_LENGTH = 256
PASSWORD_MIN_LENGTH = 12
DEFAULT_LOAN_DURATION_DAYS = 28


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


def _serialize_audit_event(event):
    return {
        "id": event.id,
        "actor_user_id": event.actor_user_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "request_id": event.request_id,
        "remote_addr": event.remote_addr,
        "client_ip_resolved": event.client_ip_resolved,
        "forwarded_chain": event.forwarded_chain,
        "scheme": event.scheme,
        "host": event.host,
        "payload_json": event.payload_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _serialize_loan(loan):
    return {
        "id": loan.id,
        "borrower_user_id": loan.borrower_user_id,
        "jigsaw_id": loan.jigsaw_id,
        "checked_out_at": loan.checked_out_at.isoformat() if loan.checked_out_at else None,
        "due_at": loan.due_at.isoformat() if loan.due_at else None,
        "returned_at": loan.returned_at.isoformat() if loan.returned_at else None,
        "status": loan.status.value,
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


def _contains_control_characters(value):
    return any((ord(character) < 32 or ord(character) == 127) for character in value)


def _validate_email(value, field_name="email"):
    if not isinstance(value, str) or not value.strip():
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a non-empty string"}],
        )

    normalized_email = value.strip().lower()
    if len(normalized_email) > USER_EMAIL_MAX_LENGTH:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": f"must be {USER_EMAIL_MAX_LENGTH} characters or fewer"}],
        )

    if not EMAIL_REGEX.fullmatch(normalized_email):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a valid email address"}],
        )

    return normalized_email, None


def _validate_login_email(value):
    if not isinstance(value, str) or not value.strip():
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": "must be a non-empty string"}],
        )

    normalized_email = value.strip().lower()
    if len(normalized_email) > USER_EMAIL_MAX_LENGTH:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": f"must be {USER_EMAIL_MAX_LENGTH} characters or fewer"}],
        )

    if _contains_control_characters(normalized_email):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": "contains unsupported control characters"}],
        )

    return normalized_email, None


def _validate_display_name(value):
    if value is None:
        return None, None

    if not isinstance(value, str):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "display_name", "issue": "must be a string or null"}],
        )

    normalized_value = value.strip()
    if not normalized_value:
        return None, None

    if len(normalized_value) > DISPLAY_NAME_MAX_LENGTH:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "display_name", "issue": f"must be {DISPLAY_NAME_MAX_LENGTH} characters or fewer"}],
        )

    if _contains_control_characters(normalized_value):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "display_name", "issue": "contains unsupported control characters"}],
        )

    if "<" in normalized_value or ">" in normalized_value:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "display_name", "issue": "must not contain angle brackets"}],
        )

    return normalized_value, None


def _validate_password(value, *, require_min_length=False):
    if not isinstance(value, str) or not value:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "password", "issue": "must be a non-empty string"}],
        )

    if len(value) > PASSWORD_MAX_LENGTH:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "password", "issue": f"must be {PASSWORD_MAX_LENGTH} characters or fewer"}],
        )

    if _contains_control_characters(value):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "password", "issue": "contains unsupported control characters"}],
        )

    if require_min_length and len(value) < PASSWORD_MIN_LENGTH:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "password", "issue": f"must be at least {PASSWORD_MIN_LENGTH} characters"}],
        )

    return value, None


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


def _parse_positive_integer(value, field_name):
    if not isinstance(value, int) or value <= 0:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a positive integer"}],
        )

    return value, None


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

    email, error = _validate_login_email(payload.get("email"))
    if error is not None:
        return error

    password, error = _validate_password(payload.get("password"))
    if error is not None:
        return error

    db_session = get_session()
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
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
    csrf_token = session.get("csrf_token")
    if not csrf_token:
        csrf_token = token_urlsafe(24)
        session["csrf_token"] = csrf_token

    return _success_response(
        {
            "user": _serialize_user(g.current_user, g.current_user_roles),
            "csrf_token": csrf_token,
        }
    )


@api_v1_bp.patch("/auth/me")
@require_auth
def update_auth_me():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    if "email" in payload:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "email", "issue": "cannot be changed via this endpoint"}],
        )

    if not any(field in payload for field in {"display_name", "current_password", "new_password"}):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "payload", "issue": "must include display_name or password fields"}],
        )

    updated_fields = []

    if "display_name" in payload:
        display_name, error = _validate_display_name(payload.get("display_name"))
        if error is not None:
            return error
        g.current_user.display_name = display_name
        updated_fields.append("display_name")

    password_change_requested = "current_password" in payload or "new_password" in payload
    if password_change_requested:
        current_password, error = _validate_password(payload.get("current_password"))
        if error is not None:
            return error

        new_password, error = _validate_password(payload.get("new_password"), require_min_length=True)
        if error is not None:
            return error

        if not g.current_user.check_password(current_password):
            return _error_response("forbidden", "Current password is incorrect.", 403)

        if current_password == new_password:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "new_password", "issue": "must be different from current_password"}],
            )

        g.current_user.set_password(new_password)
        updated_fields.append("password")

    db_session = get_session()
    _record_audit_event(
        action="auth.profile_updated",
        entity_type="user",
        entity_id=g.current_user.id,
        payload={"updated_fields": sorted(updated_fields)},
    )
    db_session.commit()

    csrf_token = session.get("csrf_token")
    return _success_response(
        {
            "user": _serialize_user(g.current_user, g.current_user_roles),
            "csrf_token": csrf_token,
        }
    )


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


@api_v1_bp.get("/audit-events")
@require_role("administrator")
def list_audit_events():
    raw_limit = request.args.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "limit", "issue": "must be an integer"}],
        )

    if limit < 1 or limit > 200:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "limit", "issue": "must be between 1 and 200"}],
        )

    db_session = get_session()
    events = db_session.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).scalars().all()
    payload = [_serialize_audit_event(event) for event in events]
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

    email, error = _validate_email(payload.get("email"))
    if error is not None:
        return error

    password, error = _validate_password(payload.get("password"), require_min_length=True)
    if error is not None:
        return error

    display_name, error = _validate_display_name(payload.get("display_name"))
    if error is not None:
        return error

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
    user.set_password(password)
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

    updatable_fields = {"email", "display_name", "is_active", "roles", "password"}
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
        normalized_email, error = _validate_email(payload.get("email"))
        if error is not None:
            return error
        existing_user = db_session.execute(select(User).where(User.email == normalized_email, User.id != user.id)).scalar_one_or_none()
        if existing_user is not None:
            return _error_response("conflict", "A user with this email already exists.", 409)
        user.email = normalized_email

    if "display_name" in payload:
        display_name, error = _validate_display_name(payload.get("display_name"))
        if error is not None:
            return error
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

        if user.id == g.current_user.id and is_active is False:
            return _error_response("conflict", "You cannot deactivate your own account.", 409)

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

    if "password" in payload:
        password, error = _validate_password(payload.get("password"), require_min_length=True)
        if error is not None:
            return error
        user.set_password(password)

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


@api_v1_bp.get("/loans")
@require_role("administrator")
def list_loans():
    db_session = get_session()
    loans = db_session.execute(select(Loan).order_by(Loan.id.desc())).scalars().all()
    payload = [_serialize_loan(loan) for loan in loans]
    return _success_response(payload)


@api_v1_bp.post("/loans")
@require_role("administrator")
def create_loan():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    borrower_user_id, error = _parse_positive_integer(payload.get("borrower_user_id"), "borrower_user_id")
    if error is not None:
        return error

    jigsaw_id, error = _parse_positive_integer(payload.get("jigsaw_id"), "jigsaw_id")
    if error is not None:
        return error

    db_session = get_session()
    borrower = db_session.get(User, borrower_user_id)
    if borrower is None:
        return _error_response("not_found", "Borrower was not found.", 404)

    if not borrower.is_active:
        return _error_response("conflict", "Borrower account is inactive.", 409)

    borrower_roles = _get_role_names_for_user_id(borrower.id)
    if "borrower" not in borrower_roles and "administrator" not in borrower_roles:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "borrower_user_id", "issue": "must reference a borrower or administrator user"}],
        )

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if jigsaw.status != JigsawStatus.AVAILABLE:
        return _error_response("conflict", "Jigsaw is not available for loan.", 409)

    existing_active_loan = db_session.execute(
        select(Loan).where(Loan.jigsaw_id == jigsaw.id, Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
    ).scalar_one_or_none()
    if existing_active_loan is not None:
        return _error_response("conflict", "Jigsaw already has an active loan.", 409)

    checked_out_at = datetime.now(timezone.utc)
    due_at = checked_out_at + timedelta(days=DEFAULT_LOAN_DURATION_DAYS)

    loan = Loan(
        borrower_user_id=borrower.id,
        jigsaw_id=jigsaw.id,
        checked_out_at=checked_out_at,
        due_at=due_at,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    jigsaw.status = JigsawStatus.ON_LOAN
    db_session.flush()

    _record_audit_event(
        action="loan.created",
        entity_type="loan",
        entity_id=loan.id,
        payload={
            "borrower_user_id": borrower.id,
            "jigsaw_id": jigsaw.id,
            "checked_out_at": loan.checked_out_at.isoformat(),
            "due_at": loan.due_at.isoformat(),
        },
    )
    db_session.commit()

    return _success_response(_serialize_loan(loan), status_code=201)


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
