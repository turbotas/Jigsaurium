import json
import base64
import hashlib
import mimetypes
import re
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from secrets import token_urlsafe
from functools import wraps

from flask import Blueprint, current_app, g, request, session
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.exc import DataError

from app.db import get_session
from app.models import AiUsageEvent, AuditEvent, Jigsaw, JigsawDiaryEntry, JigsawImage, Loan, Role, User, UserRole
from app.models.jigsaw import JigsawStatus
from app.models.loan import LoanStatus


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
USER_EMAIL_MAX_LENGTH = 255
DISPLAY_NAME_MAX_LENGTH = 255
PASSWORD_MAX_LENGTH = 256
PASSWORD_MIN_LENGTH = 12
DEFAULT_LOAN_DURATION_DAYS = 28
JIGSAW_TITLE_MAX_LENGTH = 255
JIGSAW_MANUFACTURER_MAX_LENGTH = 255
JIGSAW_ARTIST_MAX_LENGTH = 255
JIGSAW_DIMENSIONS_MAX_LENGTH = 64
JIGSAW_TAGS_MAX_LENGTH = 512
JIGSAW_DESCRIPTION_MAX_LENGTH = 4000
JIGSAW_IMAGE_TAG_MAX_LENGTH = 64
JIGSAW_IMAGE_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_JIGSAW_IMAGE_TAG = "untagged"
IMAGE_BROWSER_TAG_BOX = "Box"
IMAGE_BROWSER_TAG_COMPLETED = "Completed"
ZIP_UPLOAD_MIME_TYPES = {"application/zip", "application/x-zip-compressed", "multipart/x-zip"}
AI_IMAGE_CREATE_OPERATION = "image_to_jigsaw"
AI_USAGE_STATUS_SUCCESS = "success"
AI_USAGE_STATUS_ERROR = "error"
AI_USAGE_STATUS_BLOCKED = "blocked"
AI_BOX_IMAGE_TAG = "Box"
DIARY_ENTRY_NOTES_MAX_LENGTH = 4000
DIARY_ENTRY_DIFFICULTY_MIN = 1
DIARY_ENTRY_DIFFICULTY_MAX = 5


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
        "manufacturer": jigsaw.manufacturer,
        "artist": jigsaw.artist,
        "dimensions_cm": jigsaw.dimensions_cm,
        "description": jigsaw.description,
        "piece_count": jigsaw.piece_count,
        "condition": jigsaw.condition,
        "status": jigsaw.status.value,
        "tags": jigsaw.tags,
        "last_completed_at": jigsaw.last_completed_at.isoformat() if jigsaw.last_completed_at else None,
    }


def _serialize_jigsaw_image(image):
    return {
        "id": image.id,
        "jigsaw_id": image.jigsaw_id,
        "tag": image.tag,
        "filename": image.filename,
        "mime_type": image.mime_type,
        "content_url": f"/api/v1/images/{image.id}/content",
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


def _serialize_diary_entry(entry):
    return {
        "id": entry.id,
        "jigsaw_id": entry.jigsaw_id,
        "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
        "difficulty": entry.difficulty,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
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


def _validate_optional_text_field(value, *, field_name, max_length):
    if value is None:
        return None, None

    if not isinstance(value, str):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a string or null"}],
        )

    normalized = value.strip()
    if not normalized:
        return None, None

    if len(normalized) > max_length:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": f"must be {max_length} characters or fewer"}],
        )

    if _contains_control_characters(normalized):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "contains unsupported control characters"}],
        )

    return normalized, None


def _parse_optional_iso_datetime(value, field_name):
    if value is None:
        return None, None

    if isinstance(value, str) and not value.strip():
        return None, None

    if not isinstance(value, str):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be an ISO 8601 datetime string or null"}],
        )

    raw_value = value.strip()
    if raw_value.endswith("Z"):
        raw_value = raw_value[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a valid ISO 8601 datetime"}],
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed, None


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


def _parse_optional_positive_integer(value, field_name):
    if value is None:
        return None, None

    if isinstance(value, bool):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a positive integer or empty"}],
        )

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None, None
        try:
            parsed = int(normalized)
        except ValueError:
            return None, _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": field_name, "issue": "must be a positive integer or empty"}],
            )
        if parsed <= 0:
            return None, _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": field_name, "issue": "must be greater than zero when provided"}],
            )
        return parsed, None

    if not isinstance(value, int) or value <= 0:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be greater than zero when provided"}],
        )

    return value, None


def _parse_optional_difficulty(value, field_name="difficulty"):
    if value is None:
        return None, None

    if isinstance(value, bool):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be an integer between 1 and 5 or empty"}],
        )

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None, None
        try:
            parsed = int(normalized)
        except ValueError:
            return None, _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": field_name, "issue": "must be an integer between 1 and 5 or empty"}],
            )
    elif isinstance(value, int):
        parsed = value
    else:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be an integer between 1 and 5 or empty"}],
        )

    if parsed < DIARY_ENTRY_DIFFICULTY_MIN or parsed > DIARY_ENTRY_DIFFICULTY_MAX:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be between 1 and 5 when provided"}],
        )

    return parsed, None


def _is_zip_upload(upload):
    mime_type = (upload.mimetype or "").strip().lower()
    filename = (upload.filename or "").strip().lower()
    return mime_type in ZIP_UPLOAD_MIME_TYPES or filename.endswith(".zip")


def _resolve_optional_jigsaw_reference(db_session, raw_value):
    jigsaw_id, error = _parse_optional_positive_integer(raw_value, "jigsaw_id")
    if error is not None:
        return None, None, error

    if jigsaw_id is None:
        return None, None, None

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return None, None, _error_response("not_found", "Jigsaw was not found.", 404)

    return jigsaw_id, jigsaw, None


def _create_jigsaw_image_record(db_session, *, jigsaw_id, tag, filename, mime_type, image_data, image_sha256):
    image = JigsawImage(
        jigsaw_id=jigsaw_id,
        tag=tag,
        filename=filename,
        mime_type=mime_type,
        image_data=image_data,
        image_sha256=image_sha256,
    )
    db_session.add(image)
    db_session.flush()
    return image


def _extract_zip_image_items(upload):
    issues = []
    images = []

    zip_bytes = upload.read()
    if not zip_bytes:
        issues.append({"filename": upload.filename or "archive.zip", "issue": "zip file is empty"})
        return images, issues

    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue

                filename = (entry.filename or "").rsplit("/", 1)[-1].strip()
                if not filename:
                    issues.append({"filename": entry.filename or "(unknown)", "issue": "filename is missing"})
                    continue

                mime_type, _encoding = mimetypes.guess_type(filename)
                mime_type = (mime_type or "").lower()
                if not mime_type.startswith("image/"):
                    issues.append({"filename": filename, "issue": "not an image file"})
                    continue

                if entry.file_size <= 0:
                    issues.append({"filename": filename, "issue": "file must not be empty"})
                    continue

                if entry.file_size > JIGSAW_IMAGE_MAX_BYTES:
                    issues.append(
                        {
                            "filename": filename,
                            "issue": f"must be {JIGSAW_IMAGE_MAX_BYTES} bytes or fewer",
                        }
                    )
                    continue

                image_data = archive.read(entry)
                if len(image_data) > JIGSAW_IMAGE_MAX_BYTES:
                    issues.append(
                        {
                            "filename": filename,
                            "issue": f"must be {JIGSAW_IMAGE_MAX_BYTES} bytes or fewer",
                        }
                    )
                    continue

                normalized_filename, error = _validate_optional_text_field(
                    filename, field_name="filename", max_length=255
                )
                if error is not None:
                    issues.append({"filename": filename, "issue": "filename is invalid"})
                    continue

                images.append(
                    {
                        "filename": normalized_filename,
                        "mime_type": mime_type,
                        "image_data": image_data,
                        "image_sha256": _compute_image_sha256(image_data),
                        "source": upload.filename or "archive.zip",
                    }
                )
    except (zipfile.BadZipFile, OSError):
        issues.append({"filename": upload.filename or "archive.zip", "issue": "zip file is invalid"})

    return images, issues


def _extract_bulk_image_items(uploads):
    image_items = []
    issues = []

    for upload in uploads:
        if _is_zip_upload(upload):
            extracted_images, extracted_issues = _extract_zip_image_items(upload)
            image_items.extend(extracted_images)
            issues.extend(extracted_issues)
            continue

        mime_type = (upload.mimetype or "").strip().lower()
        if not mime_type.startswith("image/"):
            issues.append({"filename": upload.filename or "(unnamed)", "issue": "must be an image or zip file"})
            continue

        image_data = upload.read()
        if not image_data:
            issues.append({"filename": upload.filename or "(unnamed)", "issue": "file must not be empty"})
            continue

        if len(image_data) > JIGSAW_IMAGE_MAX_BYTES:
            issues.append(
                {
                    "filename": upload.filename or "(unnamed)",
                    "issue": f"must be {JIGSAW_IMAGE_MAX_BYTES} bytes or fewer",
                }
            )
            continue

        filename, error = _validate_optional_text_field(upload.filename, field_name="filename", max_length=255)
        if error is not None:
            issues.append({"filename": upload.filename or "(unnamed)", "issue": "filename is invalid"})
            continue

        image_items.append(
            {
                "filename": filename,
                "mime_type": mime_type,
                "image_data": image_data,
                "image_sha256": _compute_image_sha256(image_data),
                "source": upload.filename or "(unnamed)",
            }
        )

    return image_items, issues


def _build_image_content_response(image):
    response = current_app.response_class(image.image_data, mimetype=image.mime_type)
    if image.filename:
        response.headers["Content-Disposition"] = f'inline; filename="{image.filename}"'
    return response


def _compute_image_sha256(image_data):
    return hashlib.sha256(image_data).hexdigest()


def _validate_image_browser_tag(value):
    normalized, error = _validate_optional_text_field(value, field_name="tag", max_length=JIGSAW_IMAGE_TAG_MAX_LENGTH)
    if error is not None:
        return None, error
    if normalized is None:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "tag", "issue": "must be a non-empty string"}],
        )
    return normalized, None


def _to_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extract_json_object_from_text(raw_text):
    if not isinstance(raw_text, str):
        return None

    stripped = raw_text.strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = stripped[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed


def _build_ai_image_prompt():
    return (
        "You are extracting metadata from a jigsaw puzzle box image. "
        "Return strictly valid JSON with keys: "
        "title, manufacturer, artist, piece_count, tags, dimensions_cm, description. "
        "Use null when unknown. "
        "piece_count must be an integer when present. "
        "tags must be either a comma-separated string or an array of short strings. "
        "Do not include markdown or extra commentary."
    )


def _build_ai_usage_costs(result_payload):
    usage = result_payload.get("usage") if isinstance(result_payload, dict) else {}
    usage = usage if isinstance(usage, dict) else {}

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")

    prompt_tokens = int(prompt_tokens) if isinstance(prompt_tokens, int) else None
    completion_tokens = int(completion_tokens) if isinstance(completion_tokens, int) else None
    total_tokens = int(total_tokens) if isinstance(total_tokens, int) else None

    provider_cost = None
    for candidate in (
        usage.get("total_cost_usd"),
        usage.get("cost_usd"),
        usage.get("cost"),
        result_payload.get("cost_usd") if isinstance(result_payload, dict) else None,
        result_payload.get("cost") if isinstance(result_payload, dict) else None,
    ):
        provider_cost = _to_decimal(candidate)
        if provider_cost is not None:
            break

    computed_cost = None
    final_cost = provider_cost
    if final_cost is None:
        final_cost = Decimal("0")

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "provider_cost_usd": provider_cost,
        "computed_cost_usd": computed_cost,
        "final_cost_usd": final_cost,
    }


def _get_daily_ai_spend(db_session):
    now = datetime.now(timezone.utc)
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    spend = db_session.execute(
        select(func.coalesce(func.sum(AiUsageEvent.final_cost_usd), 0)).where(
            AiUsageEvent.operation == AI_IMAGE_CREATE_OPERATION,
            AiUsageEvent.status == AI_USAGE_STATUS_SUCCESS,
            AiUsageEvent.created_at >= day_start,
            AiUsageEvent.created_at < day_end,
        )
    ).scalar_one()
    return _to_decimal(spend) or Decimal("0")


def _record_ai_usage_event(
    *,
    db_session,
    image_id,
    status,
    model,
    endpoint_url,
    prompt_tokens=None,
    completion_tokens=None,
    total_tokens=None,
    provider_cost_usd=None,
    computed_cost_usd=None,
    final_cost_usd=None,
    error_code=None,
    error_message=None,
    payload=None,
):
    payload_json = json.dumps(payload, sort_keys=True) if payload is not None else None
    usage_event = AiUsageEvent(
        actor_user_id=getattr(g.current_user, "id", None),
        image_id=image_id,
        operation=AI_IMAGE_CREATE_OPERATION,
        status=status,
        model=model,
        endpoint_url=endpoint_url,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        provider_cost_usd=provider_cost_usd,
        computed_cost_usd=computed_cost_usd,
        final_cost_usd=final_cost_usd if final_cost_usd is not None else Decimal("0"),
        error_code=error_code,
        error_message=error_message,
        payload_json=payload_json,
        request_id=g.request_id,
    )
    db_session.add(usage_event)
    db_session.flush()
    return usage_event


def _normalize_ai_tags(raw_tags):
    if raw_tags is None:
        return None, None

    if isinstance(raw_tags, str):
        return _validate_optional_text_field(raw_tags, field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)

    if isinstance(raw_tags, list):
        normalized_items = []
        for item in raw_tags:
            tag, error = _validate_optional_text_field(item, field_name="tags", max_length=64)
            if error is not None:
                return None, _error_response(
                    "validation_error",
                    "Invalid request payload.",
                    422,
                    [{"field": "tags", "issue": "must be a string, null, or list of short strings"}],
                )
            if tag:
                normalized_items.append(tag)

        joined = ", ".join(normalized_items)
        return _validate_optional_text_field(joined, field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)

    return None, _error_response(
        "validation_error",
        "Invalid request payload.",
        422,
        [{"field": "tags", "issue": "must be a string, null, or list of strings"}],
    )


def _normalize_ai_jigsaw_payload(raw_payload):
    if not isinstance(raw_payload, dict):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "ai_response", "issue": "must be a JSON object"}],
        )

    title, error = _validate_optional_text_field(raw_payload.get("title"), field_name="title", max_length=JIGSAW_TITLE_MAX_LENGTH)
    if error is not None:
        return None, error

    manufacturer_source = raw_payload.get("manufacturer")
    if manufacturer_source is None:
        manufacturer_source = raw_payload.get("publisher")
    manufacturer, error = _validate_optional_text_field(
        manufacturer_source,
        field_name="manufacturer",
        max_length=JIGSAW_MANUFACTURER_MAX_LENGTH,
    )
    if error is not None:
        return None, error

    artist, error = _validate_optional_text_field(raw_payload.get("artist"), field_name="artist", max_length=JIGSAW_ARTIST_MAX_LENGTH)
    if error is not None:
        return None, error

    dimensions_cm, error = _validate_optional_text_field(
        raw_payload.get("dimensions_cm"),
        field_name="dimensions_cm",
        max_length=JIGSAW_DIMENSIONS_MAX_LENGTH,
    )
    if error is not None:
        return None, error

    description, error = _validate_optional_text_field(
        raw_payload.get("description"),
        field_name="description",
        max_length=JIGSAW_DESCRIPTION_MAX_LENGTH,
    )
    if error is not None:
        return None, error

    piece_count, error = _parse_optional_positive_integer(raw_payload.get("piece_count"), "piece_count")
    if error is not None:
        return None, error

    tags, error = _normalize_ai_tags(raw_payload.get("tags"))
    if error is not None:
        return None, error

    return {
        "title": title,
        "manufacturer": manufacturer,
        "artist": artist,
        "dimensions_cm": dimensions_cm,
        "description": description,
        "piece_count": piece_count,
        "tags": tags,
    }, None


def _infer_jigsaw_metadata_from_image(image):
    if not current_app.config.get("AI_ENABLED", False):
        raise RuntimeError("AI image inference is disabled")

    api_key = (current_app.config.get("AI_API_KEY") or "").strip()
    endpoint_url = (current_app.config.get("AI_ENDPOINT_URL") or "").strip()
    model = (current_app.config.get("AI_MODEL") or "").strip()
    timeout_seconds = int(current_app.config.get("AI_TIMEOUT_SECONDS") or 60)

    if not api_key or not endpoint_url or not model:
        raise RuntimeError("AI image inference configuration is incomplete")

    image_base64 = base64.b64encode(image.image_data).decode("ascii")
    request_payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _build_ai_image_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract jigsaw metadata from this image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image.mime_type};base64,{image_base64}",
                        },
                    },
                ],
            },
        ],
    }

    body = json.dumps(request_payload).encode("utf-8")
    http_request = urllib.request.Request(
        endpoint_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"AI provider returned HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError("AI provider request failed") from error

    try:
        result_payload = json.loads(response_raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("AI provider returned invalid JSON") from error

    choice = None
    choices = result_payload.get("choices") if isinstance(result_payload, dict) else None
    if isinstance(choices, list) and choices:
        choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None

    parsed_payload = _extract_json_object_from_text(content)
    if parsed_payload is None:
        raise RuntimeError("AI provider did not return a valid metadata JSON object")

    cost_payload = _build_ai_usage_costs(result_payload)
    return {
        "metadata": parsed_payload,
        "prompt_tokens": cost_payload["prompt_tokens"],
        "completion_tokens": cost_payload["completion_tokens"],
        "total_tokens": cost_payload["total_tokens"],
        "provider_cost_usd": cost_payload["provider_cost_usd"],
        "computed_cost_usd": cost_payload["computed_cost_usd"],
        "final_cost_usd": cost_payload["final_cost_usd"],
        "model": model,
        "endpoint_url": endpoint_url,
    }


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
        stmt = stmt.where(
            Jigsaw.title.ilike(pattern)
            | Jigsaw.tags.ilike(pattern)
            | Jigsaw.manufacturer.ilike(pattern)
            | Jigsaw.artist.ilike(pattern)
        )

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

    title, error = _validate_optional_text_field(payload.get("title"), field_name="title", max_length=JIGSAW_TITLE_MAX_LENGTH)
    if error is not None:
        return error

    piece_count, error = _parse_optional_positive_integer(payload.get("piece_count"), "piece_count")
    if error is not None:
        return error

    raw_status = payload.get("status")
    if raw_status is None or (isinstance(raw_status, str) and not raw_status.strip()):
        status = JigsawStatus.AVAILABLE
    else:
        status, error = _parse_jigsaw_status(raw_status)
        if error is not None:
            return error

    manufacturer, error = _validate_optional_text_field(
        payload.get("manufacturer"), field_name="manufacturer", max_length=JIGSAW_MANUFACTURER_MAX_LENGTH
    )
    if error is not None:
        return error

    artist, error = _validate_optional_text_field(
        payload.get("artist"), field_name="artist", max_length=JIGSAW_ARTIST_MAX_LENGTH
    )
    if error is not None:
        return error

    dimensions_cm, error = _validate_optional_text_field(
        payload.get("dimensions_cm"), field_name="dimensions_cm", max_length=JIGSAW_DIMENSIONS_MAX_LENGTH
    )
    if error is not None:
        return error

    description, error = _validate_optional_text_field(
        payload.get("description"), field_name="description", max_length=JIGSAW_DESCRIPTION_MAX_LENGTH
    )
    if error is not None:
        return error

    condition, error = _validate_optional_text_field(payload.get("condition"), field_name="condition", max_length=64)
    if error is not None:
        return error

    tags, error = _validate_optional_text_field(payload.get("tags"), field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)
    if error is not None:
        return error

    last_completed_at, error = _parse_optional_iso_datetime(payload.get("last_completed_at"), "last_completed_at")
    if error is not None:
        return error

    db_session = get_session()
    jigsaw = Jigsaw(
        title=title,
        manufacturer=manufacturer,
        artist=artist,
        dimensions_cm=dimensions_cm,
        description=description,
        piece_count=piece_count,
        condition=condition,
        status=status,
        tags=tags,
        last_completed_at=last_completed_at,
    )
    db_session.add(jigsaw)
    db_session.flush()

    _record_audit_event(
        action="jigsaw.created",
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={
            "title": jigsaw.title,
            "piece_count": piece_count,
            "status": status.value,
            "manufacturer": jigsaw.manufacturer,
            "artist": jigsaw.artist,
            "dimensions_cm": jigsaw.dimensions_cm,
            "last_completed_at": jigsaw.last_completed_at.isoformat() if jigsaw.last_completed_at else None,
        },
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

    updatable_fields = {
        "title",
        "manufacturer",
        "artist",
        "dimensions_cm",
        "description",
        "piece_count",
        "condition",
        "status",
        "tags",
        "last_completed_at",
    }
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
        if len(title.strip()) > JIGSAW_TITLE_MAX_LENGTH:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "title", "issue": f"must be {JIGSAW_TITLE_MAX_LENGTH} characters or fewer"}],
            )
        jigsaw.title = title.strip()

    if "manufacturer" in payload:
        manufacturer, error = _validate_optional_text_field(
            payload.get("manufacturer"), field_name="manufacturer", max_length=JIGSAW_MANUFACTURER_MAX_LENGTH
        )
        if error is not None:
            return error
        jigsaw.manufacturer = manufacturer

    if "artist" in payload:
        artist, error = _validate_optional_text_field(
            payload.get("artist"), field_name="artist", max_length=JIGSAW_ARTIST_MAX_LENGTH
        )
        if error is not None:
            return error
        jigsaw.artist = artist

    if "dimensions_cm" in payload:
        dimensions_cm, error = _validate_optional_text_field(
            payload.get("dimensions_cm"), field_name="dimensions_cm", max_length=JIGSAW_DIMENSIONS_MAX_LENGTH
        )
        if error is not None:
            return error
        jigsaw.dimensions_cm = dimensions_cm

    if "description" in payload:
        description, error = _validate_optional_text_field(
            payload.get("description"), field_name="description", max_length=JIGSAW_DESCRIPTION_MAX_LENGTH
        )
        if error is not None:
            return error
        jigsaw.description = description

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
        condition, error = _validate_optional_text_field(payload.get("condition"), field_name="condition", max_length=64)
        if error is not None:
            return error
        jigsaw.condition = condition

    if "status" in payload:
        status, error = _parse_jigsaw_status(payload.get("status"))
        if error is not None:
            return error
        jigsaw.status = status

    if "tags" in payload:
        tags, error = _validate_optional_text_field(payload.get("tags"), field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)
        if error is not None:
            return error
        jigsaw.tags = tags

    if "last_completed_at" in payload:
        last_completed_at, error = _parse_optional_iso_datetime(payload.get("last_completed_at"), "last_completed_at")
        if error is not None:
            return error
        jigsaw.last_completed_at = last_completed_at

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


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>/images")
@require_role("administrator")
def list_jigsaw_images(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    images = db_session.execute(select(JigsawImage).where(JigsawImage.jigsaw_id == jigsaw.id).order_by(JigsawImage.id.desc())).scalars().all()
    payload = [_serialize_jigsaw_image(image) for image in images]
    return _success_response(payload)


@api_v1_bp.post("/jigsaws/<int:jigsaw_id>/images")
@require_role("administrator")
def create_jigsaw_image(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    tag, error = _validate_optional_text_field(
        request.form.get("tag"), field_name="tag", max_length=JIGSAW_IMAGE_TAG_MAX_LENGTH
    )
    if error is not None:
        return error
    if tag is None:
        tag = DEFAULT_JIGSAW_IMAGE_TAG

    upload = request.files.get("image")
    if upload is None:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "file is required"}],
        )

    mime_type = (upload.mimetype or "").strip().lower()
    if not mime_type.startswith("image/"):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "must be an image content type"}],
        )

    image_data = upload.read()
    if not image_data:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "file must not be empty"}],
        )

    if len(image_data) > JIGSAW_IMAGE_MAX_BYTES:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": f"must be {JIGSAW_IMAGE_MAX_BYTES} bytes or fewer"}],
        )

    filename, error = _validate_optional_text_field(
        upload.filename, field_name="filename", max_length=255
    )
    if error is not None:
        return error

    image_sha256 = _compute_image_sha256(image_data)
    duplicate_image = db_session.execute(
        select(JigsawImage).where(JigsawImage.image_sha256 == image_sha256).order_by(JigsawImage.id.asc())
    ).scalar_one_or_none()
    if duplicate_image is not None:
        _record_audit_event(
            action="jigsaw.image_duplicate_ignored",
            entity_type="jigsaw_image",
            entity_id=duplicate_image.id,
            payload={
                "jigsaw_id": jigsaw.id,
                "source_filename": filename,
                "duplicate_hash": image_sha256,
            },
        )
        db_session.commit()
        return _success_response(_serialize_jigsaw_image(duplicate_image))

    try:
        image = _create_jigsaw_image_record(
            db_session,
            jigsaw_id=jigsaw.id,
            tag=tag,
            filename=filename,
            mime_type=mime_type,
            image_data=image_data,
            image_sha256=image_sha256,
        )

        _record_audit_event(
            action="jigsaw.image_created",
            entity_type="jigsaw_image",
            entity_id=image.id,
            payload={
                "jigsaw_id": jigsaw.id,
                "tag": image.tag,
                "mime_type": image.mime_type,
                "size_bytes": len(image_data),
            },
        )
        db_session.commit()
    except DataError:
        db_session.rollback()
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "is too large to store"}],
        )

    return _success_response(_serialize_jigsaw_image(image), status_code=201)


@api_v1_bp.get("/image-library/images")
@require_role("administrator")
def list_image_library_images():
    raw_limit = request.args.get("limit", "200")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "limit", "issue": "must be an integer"}],
        )

    if limit < 1 or limit > 500:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "limit", "issue": "must be between 1 and 500"}],
        )

    db_session = get_session()
    images = db_session.execute(select(JigsawImage).order_by(JigsawImage.id.desc()).limit(limit)).scalars().all()
    payload = [_serialize_jigsaw_image(image) for image in images]
    return _success_response(payload)


@api_v1_bp.post("/image-library/uploads")
@require_role("administrator")
def upload_image_library_items():
    db_session = get_session()

    jigsaw_id, _jigsaw, error = _resolve_optional_jigsaw_reference(db_session, request.form.get("jigsaw_id"))
    if error is not None:
        return error

    tag, error = _validate_optional_text_field(
        request.form.get("tag"), field_name="tag", max_length=JIGSAW_IMAGE_TAG_MAX_LENGTH
    )
    if error is not None:
        return error
    if tag is None:
        tag = DEFAULT_JIGSAW_IMAGE_TAG

    uploads = request.files.getlist("files")
    if not uploads:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "files", "issue": "at least one file is required"}],
        )

    image_items, issues = _extract_bulk_image_items(uploads)
    if not image_items:
        default_issue = "must include at least one image file or zip containing image files"
        issue_message = issues[0]["issue"] if issues else default_issue
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "files", "issue": issue_message}],
        )

    created_images = []
    created_hashes = set()

    image_hashes = sorted({item["image_sha256"] for item in image_items if item.get("image_sha256")})
    existing_images_by_hash = {}
    if image_hashes:
        existing_images = db_session.execute(
            select(JigsawImage).where(JigsawImage.image_sha256.in_(image_hashes)).order_by(JigsawImage.id.asc())
        ).scalars().all()
        for existing in existing_images:
            if existing.image_sha256 and existing.image_sha256 not in existing_images_by_hash:
                existing_images_by_hash[existing.image_sha256] = existing

    try:
        for item in image_items:
            image_sha256 = item.get("image_sha256")
            if image_sha256 and image_sha256 in existing_images_by_hash:
                issues.append(
                    {
                        "filename": item["filename"] or "(unnamed)",
                        "issue": "duplicate image content already exists",
                    }
                )
                continue

            if image_sha256 and image_sha256 in created_hashes:
                issues.append(
                    {
                        "filename": item["filename"] or "(unnamed)",
                        "issue": "duplicate image content in current upload batch",
                    }
                )
                continue

            image = _create_jigsaw_image_record(
                db_session,
                jigsaw_id=jigsaw_id,
                tag=tag,
                filename=item["filename"],
                mime_type=item["mime_type"],
                image_data=item["image_data"],
                image_sha256=image_sha256,
            )
            created_images.append((image, item["source"]))
            if image_sha256:
                created_hashes.add(image_sha256)

        _record_audit_event(
            action="jigsaw.image_bulk_uploaded",
            entity_type="jigsaw_image_batch",
            entity_id="bulk",
            payload={
                "jigsaw_id": jigsaw_id,
                "tag": tag,
                "upload_file_count": len(uploads),
                "created_count": len(created_images),
                "skipped_count": len(issues),
            },
        )
        db_session.commit()
    except DataError:
        db_session.rollback()
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "files", "issue": "contains images that are too large to store"}],
        )

    created_payload = []
    for image, source in created_images:
        serialized = _serialize_jigsaw_image(image)
        serialized["source"] = source
        created_payload.append(serialized)

    return _success_response(
        {
            "created_count": len(created_payload),
            "skipped_count": len(issues),
            "created": created_payload,
            "skipped": issues,
        },
        status_code=201,
    )


@api_v1_bp.patch("/image-library/images/<int:image_id>/assign")
@require_role("administrator")
def assign_image_library_item(image_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    jigsaw_id, error = _parse_positive_integer(payload.get("jigsaw_id"), "jigsaw_id")
    if error is not None:
        return error

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if image.jigsaw_id is not None and image.jigsaw_id != jigsaw.id:
        return _error_response("conflict", "Image is already assigned to a different jigsaw.", 409)

    if image.jigsaw_id == jigsaw.id:
        return _success_response(_serialize_jigsaw_image(image))

    image.jigsaw_id = jigsaw.id

    _record_audit_event(
        action="jigsaw.image_assigned",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={
            "jigsaw_id": jigsaw.id,
            "filename": image.filename,
        },
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw_image(image))


@api_v1_bp.patch("/image-library/images/<int:image_id>/tag")
@require_role("administrator")
def set_image_library_item_tag(image_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    tag, error = _validate_image_browser_tag(payload.get("tag"))
    if error is not None:
        return error

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if image.tag == tag:
        return _success_response(_serialize_jigsaw_image(image))

    image.tag = tag
    _record_audit_event(
        action="jigsaw.image_tag_updated",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={"tag": image.tag},
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw_image(image))


@api_v1_bp.put("/image-library/images/<int:image_id>/content")
@require_role("administrator")
def replace_image_library_item_content(image_id):
    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    upload = request.files.get("image")
    if upload is None:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "file is required"}],
        )

    mime_type = (upload.mimetype or "").strip().lower()
    if not mime_type.startswith("image/"):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "must be an image content type"}],
        )

    image_data = upload.read()
    if not image_data:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "file must not be empty"}],
        )

    if len(image_data) > JIGSAW_IMAGE_MAX_BYTES:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": f"must be {JIGSAW_IMAGE_MAX_BYTES} bytes or fewer"}],
        )

    filename, error = _validate_optional_text_field(upload.filename, field_name="filename", max_length=255)
    if error is not None:
        return error

    previous_hash = image.image_sha256
    new_content_hash = _compute_image_sha256(image_data)
    image.image_data = image_data
    image.mime_type = mime_type
    image.filename = filename

    _record_audit_event(
        action="jigsaw.image_content_overwritten",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={
            "dedupe_hash_preserved": previous_hash,
            "new_content_hash": new_content_hash,
            "mime_type": image.mime_type,
            "size_bytes": len(image_data),
        },
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw_image(image))


@api_v1_bp.post("/image-library/images/<int:image_id>/create-jigsaw")
@require_role("administrator")
def create_jigsaw_from_image(image_id):
    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if image.jigsaw_id is not None:
        return _error_response("conflict", "Image is already assigned to a jigsaw.", 409)

    if not current_app.config.get("AI_ENABLED", False):
        return _error_response("conflict", "Create-from-image AI is disabled in server configuration.", 409)

    if not (current_app.config.get("AI_API_KEY") and current_app.config.get("AI_ENDPOINT_URL") and current_app.config.get("AI_MODEL")):
        return _error_response("conflict", "Create-from-image AI is not fully configured.", 409)

    budget_usd = _to_decimal(current_app.config.get("AI_DAILY_BUDGET_USD"))
    current_spend = _get_daily_ai_spend(db_session)
    if budget_usd is not None and budget_usd >= Decimal("0") and current_spend >= budget_usd:
        _record_ai_usage_event(
            db_session=db_session,
            image_id=image.id,
            status=AI_USAGE_STATUS_BLOCKED,
            model=(current_app.config.get("AI_MODEL") or "").strip() or None,
            endpoint_url=(current_app.config.get("AI_ENDPOINT_URL") or "").strip() or None,
            error_code="daily_budget_exceeded",
            error_message="Daily AI budget has been reached.",
            final_cost_usd=Decimal("0"),
            payload={"daily_spend_usd": str(current_spend), "daily_budget_usd": str(budget_usd)},
        )
        db_session.commit()
        return _error_response("conflict", "Daily AI budget has been reached for create-from-image.", 409)

    try:
        inference = _infer_jigsaw_metadata_from_image(image)
    except RuntimeError as error:
        _record_ai_usage_event(
            db_session=db_session,
            image_id=image.id,
            status=AI_USAGE_STATUS_ERROR,
            model=(current_app.config.get("AI_MODEL") or "").strip() or None,
            endpoint_url=(current_app.config.get("AI_ENDPOINT_URL") or "").strip() or None,
            error_code="provider_error",
            error_message=str(error),
            final_cost_usd=Decimal("0"),
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata extraction failed.", 502)

    normalized_payload, error = _normalize_ai_jigsaw_payload(inference.get("metadata"))
    if error is not None:
        _record_ai_usage_event(
            db_session=db_session,
            image_id=image.id,
            status=AI_USAGE_STATUS_ERROR,
            model=inference.get("model"),
            endpoint_url=inference.get("endpoint_url"),
            prompt_tokens=inference.get("prompt_tokens"),
            completion_tokens=inference.get("completion_tokens"),
            total_tokens=inference.get("total_tokens"),
            provider_cost_usd=inference.get("provider_cost_usd"),
            computed_cost_usd=inference.get("computed_cost_usd"),
            final_cost_usd=inference.get("final_cost_usd") or Decimal("0"),
            error_code="invalid_ai_payload",
            error_message="AI metadata payload could not be normalized.",
            payload={"raw_metadata": inference.get("metadata")},
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata could not be normalized.", 502)

    jigsaw = Jigsaw(
        title=normalized_payload["title"],
        manufacturer=normalized_payload["manufacturer"],
        artist=normalized_payload["artist"],
        dimensions_cm=normalized_payload["dimensions_cm"],
        description=normalized_payload["description"],
        piece_count=normalized_payload["piece_count"],
        condition=None,
        status=JigsawStatus.AVAILABLE,
        tags=normalized_payload["tags"],
        last_completed_at=None,
    )
    db_session.add(jigsaw)
    db_session.flush()

    image.jigsaw_id = jigsaw.id
    image.tag = AI_BOX_IMAGE_TAG

    usage_event = _record_ai_usage_event(
        db_session=db_session,
        image_id=image.id,
        status=AI_USAGE_STATUS_SUCCESS,
        model=inference.get("model"),
        endpoint_url=inference.get("endpoint_url"),
        prompt_tokens=inference.get("prompt_tokens"),
        completion_tokens=inference.get("completion_tokens"),
        total_tokens=inference.get("total_tokens"),
        provider_cost_usd=inference.get("provider_cost_usd"),
        computed_cost_usd=inference.get("computed_cost_usd"),
        final_cost_usd=inference.get("final_cost_usd") or Decimal("0"),
        payload={"metadata": normalized_payload, "created_jigsaw_id": jigsaw.id},
    )

    _record_audit_event(
        action="jigsaw.created_from_image",
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={
            "image_id": image.id,
            "ai_usage_event_id": usage_event.id,
            "cost_usd": str(inference.get("final_cost_usd") or Decimal("0")),
        },
    )
    db_session.commit()

    return _success_response(
        {
            "jigsaw": _serialize_jigsaw(jigsaw),
            "image": _serialize_jigsaw_image(image),
            "ai": {
                "usage_event_id": usage_event.id,
                "prompt_tokens": inference.get("prompt_tokens"),
                "completion_tokens": inference.get("completion_tokens"),
                "total_tokens": inference.get("total_tokens"),
                "final_cost_usd": str(inference.get("final_cost_usd") or Decimal("0")),
            },
        },
        status_code=201,
    )


@api_v1_bp.get("/images/<int:image_id>/content")
@require_auth
def get_image_content(image_id):
    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if image.jigsaw_id is not None:
        jigsaw = db_session.get(Jigsaw, image.jigsaw_id)
        if jigsaw is None:
            return _error_response("not_found", "Jigsaw image was not found.", 404)

        if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
            return _error_response("not_found", "Jigsaw image was not found.", 404)

    return _build_image_content_response(image)


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>/images/<int:image_id>/content")
@require_auth
def get_jigsaw_image_content(jigsaw_id, image_id):
    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None or image.jigsaw_id != jigsaw_id:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    return _build_image_content_response(image)


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>/diary-entries")
@require_auth
def list_diary_entries(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    entries = db_session.execute(
        select(JigsawDiaryEntry)
        .where(JigsawDiaryEntry.jigsaw_id == jigsaw.id)
        .order_by(JigsawDiaryEntry.completed_at.desc(), JigsawDiaryEntry.id.desc())
    ).scalars().all()
    payload = [_serialize_diary_entry(entry) for entry in entries]
    return _success_response(payload)


@api_v1_bp.post("/jigsaws/<int:jigsaw_id>/diary-entries")
@require_role("administrator")
def create_diary_entry(jigsaw_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    completed_at, error = _parse_optional_iso_datetime(payload.get("completed_at"), "completed_at")
    if error is not None:
        return error
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)

    difficulty, error = _parse_optional_difficulty(payload.get("difficulty"))
    if error is not None:
        return error

    notes, error = _validate_optional_text_field(
        payload.get("notes"), field_name="notes", max_length=DIARY_ENTRY_NOTES_MAX_LENGTH
    )
    if error is not None:
        return error

    entry = JigsawDiaryEntry(
        jigsaw_id=jigsaw.id,
        completed_at=completed_at,
        difficulty=difficulty,
        notes=notes,
    )
    db_session.add(entry)
    db_session.flush()

    existing_last_completed_at = jigsaw.last_completed_at
    if existing_last_completed_at is not None and existing_last_completed_at.tzinfo is None:
        existing_last_completed_at = existing_last_completed_at.replace(tzinfo=timezone.utc)
    if existing_last_completed_at is None or completed_at > existing_last_completed_at:
        jigsaw.last_completed_at = completed_at

    _record_audit_event(
        action="jigsaw.diary_entry_created",
        entity_type="jigsaw_diary_entry",
        entity_id=entry.id,
        payload={
            "jigsaw_id": jigsaw.id,
            "completed_at": entry.completed_at.isoformat(),
            "difficulty": entry.difficulty,
        },
    )
    db_session.commit()

    return _success_response(_serialize_diary_entry(entry), status_code=201)


@api_v1_bp.delete("/diary-entries/<int:entry_id>")
@require_role("administrator")
def delete_diary_entry(entry_id):
    db_session = get_session()
    entry = db_session.get(JigsawDiaryEntry, entry_id)
    if entry is None:
        return _error_response("not_found", "Diary entry was not found.", 404)

    jigsaw = db_session.get(Jigsaw, entry.jigsaw_id)
    serialized = _serialize_diary_entry(entry)

    db_session.delete(entry)
    db_session.flush()

    if jigsaw is not None:
        latest_completed_at = db_session.execute(
            select(func.max(JigsawDiaryEntry.completed_at)).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id)
        ).scalar_one()
        jigsaw.last_completed_at = latest_completed_at

    _record_audit_event(
        action="jigsaw.diary_entry_deleted",
        entity_type="jigsaw_diary_entry",
        entity_id=entry_id,
        payload={"jigsaw_id": serialized["jigsaw_id"]},
    )
    db_session.commit()

    return _success_response(serialized)


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


@api_v1_bp.delete("/jigsaws/<int:jigsaw_id>/permanent")
@require_role("administrator")
def delete_jigsaw_permanently(jigsaw_id):
    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    has_any_loans = db_session.execute(
        select(Loan.id).where(Loan.jigsaw_id == jigsaw.id).limit(1)
    ).scalar_one_or_none()
    if has_any_loans is not None:
        return _error_response(
            "conflict",
            "Jigsaw cannot be permanently deleted because it has loan history.",
            409,
        )

    image_count = db_session.execute(
        select(func.count()).select_from(JigsawImage).where(JigsawImage.jigsaw_id == jigsaw.id)
    ).scalar_one()
    diary_count = db_session.execute(
        select(func.count()).select_from(JigsawDiaryEntry).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id)
    ).scalar_one()

    db_session.execute(sa_delete(JigsawImage).where(JigsawImage.jigsaw_id == jigsaw.id))
    db_session.execute(sa_delete(JigsawDiaryEntry).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id))
    db_session.delete(jigsaw)

    _record_audit_event(
        action="jigsaw.deleted",
        entity_type="jigsaw",
        entity_id=jigsaw_id,
        payload={
            "deleted_image_count": int(image_count or 0),
            "deleted_diary_entry_count": int(diary_count or 0),
        },
    )
    db_session.commit()

    return _success_response({"id": jigsaw_id, "deleted": True})
