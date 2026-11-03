import json
import base64
import hashlib
import mimetypes
import threading
import time
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from secrets import compare_digest, token_urlsafe
from functools import wraps

from flask import Blueprint, current_app, g, request, session
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import delete as sa_delete
from sqlalchemy import case, func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import DataError, OperationalError

from app.db import get_session
from app.database_backups import (
    BACKUP_COMPRESSION_BZIP2,
    BACKUP_COMPRESSION_GZIP,
    BACKUP_COMPRESSION_NONE,
    DEFAULT_BACKUP_APP_NAME,
    build_backup_filename,
    build_mysql_compatible_backup_sql,
    compress_backup_payload,
    normalize_environment_label,
    normalize_backup_compression,
    resolve_backup_root_path,
)
from app.image_embeddings import (
    build_model_key,
    compute_content_sha256,
    compute_image_embedding,
    cosine_similarity,
    embedding_runtime_error,
)
from app.models import (
    AiUsageEvent,
    AuditEvent,
    BlockedIp,
    DatabaseBackup,
    BulkAiCreateJob,
    BulkAiCreateJobItem,
    ImageEmbedding,
    ImageEmbeddingJob,
    Jigsaw,
    JigsawDiaryEntry,
    JigsawImage,
    Loan,
    Role,
    User,
    UserSession,
    UserRole,
)
from app.models.jigsaw import JigsawStatus
from app.models.loan import LoanStatus
from app.request_security import MANUAL_BLOCK_SOURCE, normalize_ip_address, upsert_blocked_ip

import jwt

try:  # pragma: no cover - optional dependency fallback
    from PIL import Image, ImageOps, UnidentifiedImageError
    from PIL import DecompressionBombError
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        pass

    class DecompressionBombError(Exception):
        pass

try:  # pragma: no cover - optional HEIF/HEIC decoder plugin
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover
    register_heif_opener = None

if Image is not None and register_heif_opener is not None:  # pragma: no cover - registration side effect only
    try:
        register_heif_opener()
    except Exception:
        register_heif_opener = None


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
USER_EMAIL_MAX_LENGTH = 255
DISPLAY_NAME_MAX_LENGTH = 255
PASSWORD_MAX_LENGTH = 256
PASSWORD_MIN_LENGTH = 12
DEFAULT_LOAN_DURATION_DAYS = 28
JIGSAW_TITLE_MAX_LENGTH = 255
JIGSAW_SERIES_NAME_MAX_LENGTH = 255
JIGSAW_SERIES_NUMBER_MAX_LENGTH = 64
JIGSAW_MANUFACTURER_MAX_LENGTH = 255
JIGSAW_ARTIST_MAX_LENGTH = 255
JIGSAW_DIMENSIONS_MAX_LENGTH = 64
JIGSAW_TAGS_MAX_LENGTH = 512
JIGSAW_DESCRIPTION_MAX_LENGTH = 4000
JIGSAW_IMAGE_TAG_MAX_LENGTH = 64
JIGSAW_IMAGE_COMMENT_MAX_LENGTH = 2000
JIGSAW_IMAGE_MAX_BYTES = 8 * 1024 * 1024
JIGSAW_IMAGE_MAX_PIXELS = 40_000_000
DEFAULT_JIGSAW_IMAGE_TAG = "untagged"
IMAGE_BROWSER_TAG_BOX = "Box"
IMAGE_BROWSER_TAG_COMPLETED = "Completed"
IMAGE_BROWSER_TAG_BOX_SIDE = "Box side"
IMAGE_BROWSER_TAG_BOX_BACK = "Box back"
IMAGE_BROWSER_TAG_BOX_FRONT = "Box front"
IMAGE_BROWSER_TAG_REFERENCE = "Reference"
IMAGE_BROWSER_TAG_IN_PROGRESS = "In progress"
ZIP_UPLOAD_MIME_TYPES = {"application/zip", "application/x-zip-compressed", "multipart/x-zip"}
ALLOWED_RASTER_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
AI_IMAGE_CREATE_OPERATION = "image_to_jigsaw"
AI_JIGSAW_ENRICH_OPERATION = "jigsaw_enrich_from_images"
AI_USAGE_STATUS_SUCCESS = "success"
AI_USAGE_STATUS_ERROR = "error"
AI_USAGE_STATUS_BLOCKED = "blocked"
AI_BOX_IMAGE_TAG = "Box"
DIARY_ENTRY_NOTES_MAX_LENGTH = 4000
DIARY_ENTRY_DIFFICULTY_MIN = 1
DIARY_ENTRY_DIFFICULTY_MAX = 5
IMAGE_VARIANT_ORIGINAL = "original"
IMAGE_VARIANT_THUMBNAIL = "thumbnail"
IMAGE_VARIANT_PREVIEW = "preview"
THUMBNAIL_TARGET_WIDTH = 150
PREVIEW_TARGET_WIDTH = 600
IP_BLOCK_REASON_MAX_LENGTH = 255
IP_BLOCK_NOTES_MAX_LENGTH = 4000
IP_BLOCK_MAX_DURATION_HOURS = 24 * 30
STFD_JWT_ALGORITHM = "HS256"
SESSION_IDENTIFIER_KEY = "session_identifier"
SESSION_TERMINATION_REASON_LOGOUT = "logout"
SESSION_TERMINATION_REASON_EXPIRED = "expired"
SESSION_TERMINATION_REASON_ADMIN_TERMINATED = "admin_terminated"
SESSION_ACTIVITY_TOUCH_INTERVAL_SECONDS = 30
DATABASE_BACKUP_STATUS_QUEUED = "queued"
DATABASE_BACKUP_STATUS_RUNNING = "running"
DATABASE_BACKUP_STATUS_COMPLETED = "completed"
DATABASE_BACKUP_STATUS_FAILED = "failed"
DATABASE_BACKUP_FORMAT_MYSQL_SQL = "mysql_sql"

ROLE_CAPABILITIES = {
    "borrower": {
        "diary.create",
        "diary.read",
        "diary.update_own",
        "audit.read",
        "image.assign",
        "image.delete",
        "image.manage_library",
        "image.tag",
        "image.upload",
        "jigsaw.create",
        "jigsaw.enrich",
        "jigsaw.read",
        "jigsaw.update",
    },
    "member": {
        "diary.create",
        "diary.read",
        "diary.update_own",
        "audit.read",
        "image.assign",
        "image.delete",
        "image.manage_library",
        "image.tag",
        "image.upload",
        "jigsaw.create",
        "jigsaw.enrich",
        "jigsaw.read",
        "jigsaw.update",
    },
    "administrator": {
        "ai.manage",
        "audit.read",
        "diary.create",
        "diary.delete_any",
        "diary.read",
        "diary.update_any",
        "diary.update_own",
        "image.assign",
        "image.delete",
        "image.manage_library",
        "image.tag",
        "image.upload",
        "jigsaw.create",
        "jigsaw.enrich",
        "jigsaw.read",
        "jigsaw.update",
        "loan.manage",
        "user.manage",
    },
}

BULK_AI_CREATE_STATUS_QUEUED = "queued"
BULK_AI_CREATE_STATUS_RUNNING = "running"
BULK_AI_CREATE_STATUS_COMPLETED = "completed"
BULK_AI_CREATE_STATUS_FAILED = "failed"
BULK_AI_CREATE_ITEM_STATUS_QUEUED = "queued"
BULK_AI_CREATE_ITEM_STATUS_RUNNING = "running"
BULK_AI_CREATE_ITEM_STATUS_COMPLETED = "completed"
BULK_AI_CREATE_ITEM_STATUS_FAILED = "failed"

IMAGE_EMBEDDING_JOB_STATUS_QUEUED = "queued"
IMAGE_EMBEDDING_JOB_STATUS_RUNNING = "running"
IMAGE_EMBEDDING_JOB_STATUS_COMPLETED = "completed"
IMAGE_EMBEDDING_JOB_STATUS_FAILED = "failed"
IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL = "all"
IMAGE_EMBEDDING_BACKFILL_SCOPE_MISSING = "missing"

LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
LOGIN_RATE_LIMIT_BLOCK_SECONDS = 15 * 60
LOGIN_RATE_LIMIT_BLOCK_SOURCE = "auto_login_failures"
_failed_login_attempts = {}
_failed_login_attempts_lock = threading.Lock()

if Image is not None:
    Image.MAX_IMAGE_PIXELS = JIGSAW_IMAGE_MAX_PIXELS


class AiProviderRequestError(RuntimeError):
    def __init__(self, message, *, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def _success_response(data, status_code=200):
    return {"data": data, "meta": {"request_id": g.request_id}}, status_code


def _success_list_response(data, *, page, page_size, total_items, status_code=200):
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    return {
        "data": data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "request_id": g.request_id,
        },
    }, status_code


def _serialize_bulk_ai_create_job(job):
    error_summary = []
    if isinstance(job.error_summary_json, str) and job.error_summary_json.strip():
        try:
            parsed_summary = json.loads(job.error_summary_json)
            if isinstance(parsed_summary, list):
                error_summary = parsed_summary
        except json.JSONDecodeError:
            error_summary = []

    return {
        "id": job.id,
        "actor_user_id": job.actor_user_id,
        "status": job.status,
        "total_items": int(job.total_items or 0),
        "processed_items": int(job.processed_items or 0),
        "succeeded_items": int(job.succeeded_items or 0),
        "failed_items": int(job.failed_items or 0),
        "request_id": job.request_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_summary": error_summary,
    }


def _serialize_bulk_ai_create_job_item(item):
    return {
        "id": item.id,
        "job_id": item.job_id,
        "image_id": item.image_id,
        "status": item.status,
        "jigsaw_id": item.jigsaw_id,
        "attempts": int(item.attempts or 0),
        "error_code": item.error_code,
        "error_message": item.error_message,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _get_embedding_model_config():
    model_name = str(current_app.config.get("IMAGE_EMBEDDING_MODEL_NAME") or "").strip()
    model_revision = str(current_app.config.get("IMAGE_EMBEDDING_MODEL_REVISION") or "").strip()
    model_local_path = str(current_app.config.get("IMAGE_EMBEDDING_MODEL_LOCAL_PATH") or "").strip()
    local_files_only = bool(current_app.config.get("IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY", False))
    if not model_name:
        model_name = "openai/clip-vit-base-patch32"
    if not model_revision:
        model_revision = "main"
    return model_name, model_revision, build_model_key(model_name, model_revision), model_local_path, local_files_only


def _serialize_image_embedding_job(job):
    error_summary = []
    if isinstance(job.error_summary_json, str) and job.error_summary_json.strip():
        try:
            parsed_summary = json.loads(job.error_summary_json)
            if isinstance(parsed_summary, list):
                error_summary = parsed_summary
        except json.JSONDecodeError:
            error_summary = []

    return {
        "id": job.id,
        "actor_user_id": job.actor_user_id,
        "status": job.status,
        "scope": str(getattr(job, "scope", IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL) or IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL),
        "model_key": job.model_key,
        "total_items": int(job.total_items or 0),
        "processed_items": int(job.processed_items or 0),
        "succeeded_items": int(job.succeeded_items or 0),
        "failed_items": int(job.failed_items or 0),
        "request_id": job.request_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_summary": error_summary,
    }


def _refresh_image_embedding_job_counts(db_session, job_id):
    job = db_session.get(ImageEmbeddingJob, int(job_id))
    if job is None:
        return None
    return {
        "total_items": int(job.total_items or 0),
        "processed_items": int(job.processed_items or 0),
        "succeeded_items": int(job.succeeded_items or 0),
        "failed_items": int(job.failed_items or 0),
    }


def _mark_image_embedding_job_failed(app, job_id, code, message):
    with app.app_context():
        db_session = get_session()
        job = db_session.get(ImageEmbeddingJob, int(job_id))
        if job is None:
            return
        if job.status in {IMAGE_EMBEDDING_JOB_STATUS_COMPLETED, IMAGE_EMBEDDING_JOB_STATUS_FAILED}:
            return

        counters = _refresh_image_embedding_job_counts(db_session, job.id)
        if counters is not None:
            job.total_items = counters["total_items"]
            job.processed_items = counters["processed_items"]
            job.succeeded_items = counters["succeeded_items"]
            job.failed_items = counters["failed_items"]
        job.status = IMAGE_EMBEDDING_JOB_STATUS_FAILED
        job.finished_at = datetime.now(timezone.utc)
        job.error_summary_json = json.dumps(
            [{"code": str(code or "internal_error"), "message": str(message or "Embedding job failed.")}],
            sort_keys=True,
        )
        db_session.commit()


def _run_image_embedding_job(app, job_id):
    try:
        _process_image_embedding_job(app, int(job_id))
    except Exception:
        app.logger.exception("image_embedding_job_unhandled_exception", extra={"job_id": int(job_id)})
        _mark_image_embedding_job_failed(
            app,
            int(job_id),
            "internal_error",
            "Image embedding backfill job crashed before completion.",
        )


def _start_image_embedding_job_thread(app, job_id):
    worker = threading.Thread(
        target=_run_image_embedding_job,
        args=(app, int(job_id)),
        name=f"image-embedding-job-{int(job_id)}",
        daemon=True,
    )
    worker.start()


def _queue_image_embedding_job(job_id):
    _start_image_embedding_job_thread(current_app._get_current_object(), int(job_id))


def _allow_image_embeddings_test_fallback():
    return bool(current_app.config.get("TESTING", False)) and bool(
        current_app.config.get("IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK", False)
    )


def _upsert_image_embedding_for_image(
    db_session,
    image,
    *,
    model_name,
    model_revision,
    model_key,
    model_local_path,
    local_files_only,
    allow_test_fallback,
):
    if image is None:
        return None

    embedding_started = time.perf_counter()
    vector = compute_image_embedding(
        image.image_data,
        model_name=model_name,
        model_revision=model_revision,
        model_local_path=model_local_path,
        local_files_only=local_files_only,
        allow_test_fallback=allow_test_fallback,
    )
    embedding_duration_ms = max(0, int((time.perf_counter() - embedding_started) * 1000))
    now = datetime.now(timezone.utc)
    vector_json = json.dumps(vector)
    vector_dim = len(vector)
    source_content_sha256 = compute_content_sha256(image.image_data)

    insert_values = {
        "image_id": image.id,
        "model_key": model_key,
        "vector_json": vector_json,
        "vector_dim": vector_dim,
        "source_content_sha256": source_content_sha256,
        "compute_duration_ms": embedding_duration_ms,
        "created_at": now,
        "updated_at": now,
    }

    engine_bind = db_session.get_bind()
    dialect_name = str(getattr(engine_bind.dialect, "name", "") or "").lower()
    if dialect_name in {"mysql", "mariadb"}:
        insert_stmt = mysql_insert(ImageEmbedding).values(**insert_values)
        upsert_stmt = insert_stmt.on_duplicate_key_update(
            vector_json=insert_stmt.inserted.vector_json,
            vector_dim=insert_stmt.inserted.vector_dim,
            source_content_sha256=insert_stmt.inserted.source_content_sha256,
            compute_duration_ms=insert_stmt.inserted.compute_duration_ms,
            updated_at=insert_stmt.inserted.updated_at,
        )
    elif dialect_name == "sqlite":
        insert_stmt = sqlite_insert(ImageEmbedding).values(**insert_values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[ImageEmbedding.image_id, ImageEmbedding.model_key],
            set_={
                "vector_json": insert_stmt.excluded.vector_json,
                "vector_dim": insert_stmt.excluded.vector_dim,
                "source_content_sha256": insert_stmt.excluded.source_content_sha256,
                "compute_duration_ms": insert_stmt.excluded.compute_duration_ms,
                "updated_at": insert_stmt.excluded.updated_at,
            },
        )
    else:
        rows_updated = db_session.execute(
            sa_update(ImageEmbedding)
            .where(ImageEmbedding.image_id == image.id, ImageEmbedding.model_key == model_key)
            .values(
                vector_json=vector_json,
                vector_dim=vector_dim,
                source_content_sha256=source_content_sha256,
                compute_duration_ms=embedding_duration_ms,
                updated_at=now,
            )
        )
        if not rows_updated.rowcount:
            db_session.add(ImageEmbedding(**insert_values))
        db_session.flush()
        return db_session.execute(
            select(ImageEmbedding)
            .where(ImageEmbedding.image_id == image.id, ImageEmbedding.model_key == model_key)
            .limit(1)
        ).scalar_one_or_none()

    db_session.execute(upsert_stmt)
    db_session.flush()
    return db_session.execute(
        select(ImageEmbedding)
        .where(ImageEmbedding.image_id == image.id, ImageEmbedding.model_key == model_key)
        .limit(1)
    ).scalar_one_or_none()


def _db_error_code(error):
    original = getattr(error, "orig", None)
    args = getattr(original, "args", ())
    if not args:
        return None
    try:
        return int(args[0])
    except (TypeError, ValueError):
        return None


def _is_retryable_image_embedding_error(error):
    if not isinstance(error, OperationalError):
        return False
    return _db_error_code(error) in {1020, 1205, 1213}


def _refresh_image_embedding_with_retry(
    db_session,
    *,
    image_id,
    model_name,
    model_revision,
    model_key,
    model_local_path,
    local_files_only,
    allow_test_fallback,
    max_attempts=3,
):
    for attempt_index in range(max_attempts):
        image = db_session.get(JigsawImage, int(image_id))
        if image is None:
            return None

        try:
            return _upsert_image_embedding_for_image(
                db_session,
                image,
                model_name=model_name,
                model_revision=model_revision,
                model_key=model_key,
                model_local_path=model_local_path,
                local_files_only=local_files_only,
                allow_test_fallback=allow_test_fallback,
            )
        except OperationalError as error:
            db_session.rollback()
            if (not _is_retryable_image_embedding_error(error)) or (attempt_index >= (max_attempts - 1)):
                raise
    return None


def _process_image_embedding_job(app, job_id):
    with app.app_context():
        db_session = get_session()
        model_name, model_revision, model_key, model_local_path, local_files_only = _get_embedding_model_config()
        allow_test_fallback = _allow_image_embeddings_test_fallback()

        rows_updated = db_session.execute(
            sa_update(ImageEmbeddingJob)
            .where(
                ImageEmbeddingJob.id == int(job_id),
                ImageEmbeddingJob.status == IMAGE_EMBEDDING_JOB_STATUS_QUEUED,
            )
            .values(
                status=IMAGE_EMBEDDING_JOB_STATUS_RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()
        if rows_updated.rowcount == 0:
            return

        job = db_session.get(ImageEmbeddingJob, int(job_id))
        if job is None:
            return

        job_scope = str(getattr(job, "scope", IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL) or IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL)
        if job_scope == IMAGE_EMBEDDING_BACKFILL_SCOPE_MISSING:
            image_ids = db_session.execute(
                select(JigsawImage.id)
                .outerjoin(
                    ImageEmbedding,
                    (ImageEmbedding.image_id == JigsawImage.id) & (ImageEmbedding.model_key == model_key),
                )
                .where(ImageEmbedding.id.is_(None))
                .order_by(JigsawImage.id.asc())
            ).scalars().all()
        else:
            image_ids = db_session.execute(select(JigsawImage.id).order_by(JigsawImage.id.asc())).scalars().all()
        job.total_items = len(image_ids)
        job.processed_items = 0
        job.succeeded_items = 0
        job.failed_items = 0
        job.error_summary_json = None
        db_session.commit()

        errors = []
        for image_id in image_ids:
            image = db_session.get(JigsawImage, int(image_id))
            if image is None:
                job.processed_items += 1
                job.failed_items += 1
                db_session.commit()
                continue

            try:
                refreshed = _refresh_image_embedding_with_retry(
                    db_session,
                    image_id=image.id,
                    model_name=model_name,
                    model_revision=model_revision,
                    model_key=model_key,
                    model_local_path=model_local_path,
                    local_files_only=local_files_only,
                    allow_test_fallback=allow_test_fallback,
                )
                if refreshed is None:
                    job.failed_items += 1
                else:
                    job.succeeded_items += 1
            except Exception as error:
                job.failed_items += 1
                if len(errors) < 20:
                    errors.append({"image_id": image.id, "error": str(error)})

            job.processed_items += 1
            db_session.commit()

        if job.failed_items > 0:
            job.status = IMAGE_EMBEDDING_JOB_STATUS_FAILED
            if errors:
                job.error_summary_json = json.dumps(errors, sort_keys=True)
        else:
            job.status = IMAGE_EMBEDDING_JOB_STATUS_COMPLETED
            job.error_summary_json = None
        job.finished_at = datetime.now(timezone.utc)
        db_session.commit()


def _create_image_embedding_backfill_job(db_session, *, scope):
    _model_name, _model_revision, model_key, _model_local_path, _local_files_only = _get_embedding_model_config()

    job = ImageEmbeddingJob(
        actor_user_id=getattr(g.current_user, "id", None),
        status=IMAGE_EMBEDDING_JOB_STATUS_QUEUED,
        scope=scope,
        model_key=model_key,
        total_items=0,
        processed_items=0,
        succeeded_items=0,
        failed_items=0,
        request_id=g.request_id,
    )
    db_session.add(job)
    db_session.flush()

    _record_audit_event(
        action="jigsaw.image_embeddings_backfill_queued",
        entity_type="image_embedding_job",
        entity_id=job.id,
        payload={"model_key": model_key, "scope": scope},
    )
    db_session.commit()

    if bool(current_app.config.get("IMAGE_EMBEDDINGS_INLINE", False)):
        _process_image_embedding_job(current_app._get_current_object(), job.id)
    else:
        _queue_image_embedding_job(job.id)

    return db_session.get(ImageEmbeddingJob, job.id)


def _queue_bulk_ai_create_job(job_id):
    _start_bulk_ai_create_job_thread(current_app._get_current_object(), int(job_id))


def _start_bulk_ai_create_job_thread(app, job_id):
    worker = threading.Thread(
        target=_run_bulk_ai_create_job,
        args=(app, int(job_id)),
        name=f"bulk-ai-create-job-{int(job_id)}",
        daemon=True,
    )
    worker.start()


def _mark_bulk_ai_create_job_failed(app, job_id, code, message):
    with app.app_context():
        db_session = get_session()
        job = db_session.get(BulkAiCreateJob, int(job_id))
        if job is None:
            return

        if job.status in {BULK_AI_CREATE_STATUS_COMPLETED, BULK_AI_CREATE_STATUS_FAILED}:
            return

        refreshed = _refresh_bulk_ai_create_job_counters(db_session, job.id)
        job.total_items = refreshed["total_items"]
        job.processed_items = refreshed["processed_items"]
        job.succeeded_items = refreshed["succeeded_items"]
        job.failed_items = refreshed["failed_items"]
        job.status = BULK_AI_CREATE_STATUS_FAILED
        job.finished_at = datetime.now(timezone.utc)
        job.error_summary_json = json.dumps(
            [
                {
                    "code": str(code or "internal_error"),
                    "message": str(message or "Bulk create job failed."),
                }
            ],
            sort_keys=True,
        )
        db_session.commit()


def _run_bulk_ai_create_job(app, job_id):
    try:
        _process_bulk_ai_create_job(app, int(job_id))
    except Exception:
        app.logger.exception("bulk_ai_create_job_unhandled_exception", extra={"job_id": int(job_id)})
        _mark_bulk_ai_create_job_failed(
            app,
            int(job_id),
            "internal_error",
            "Bulk create job crashed before completion.",
        )


def _create_bulk_ai_create_job(db_session, image_ids):
    job = BulkAiCreateJob(
        actor_user_id=getattr(g.current_user, "id", None),
        status=BULK_AI_CREATE_STATUS_QUEUED,
        total_items=len(image_ids),
        processed_items=0,
        succeeded_items=0,
        failed_items=0,
        request_id=g.request_id,
    )
    db_session.add(job)
    db_session.flush()

    for image_id in image_ids:
        db_session.add(
            BulkAiCreateJobItem(
                job_id=job.id,
                image_id=image_id,
                status=BULK_AI_CREATE_ITEM_STATUS_QUEUED,
                attempts=0,
            )
        )

    _record_audit_event(
        action="jigsaw.bulk_create_queued",
        entity_type="bulk_ai_create_job",
        entity_id=job.id,
        payload={
            "item_count": len(image_ids),
            "image_ids": image_ids,
        },
    )
    db_session.commit()

    if bool(current_app.config.get("BULK_AI_CREATE_INLINE", False)):
        _process_bulk_ai_create_job(current_app._get_current_object(), job.id)
    else:
        _queue_bulk_ai_create_job(job.id)

    return db_session.get(BulkAiCreateJob, job.id)


def start_bulk_ai_create_worker(app):
    # Jobs are launched as dedicated daemon threads when queued.
    # This hook remains for app bootstrap compatibility.
    return


def _extract_response_status_code(response_payload):
    if isinstance(response_payload, tuple) and len(response_payload) >= 2:
        try:
            return int(response_payload[1])
        except (TypeError, ValueError):
            return 500
    return 500


def _extract_error_from_response(response_payload):
    if not isinstance(response_payload, tuple) or len(response_payload) < 1:
        return "internal_error", "Background create-from-image failed."

    body = response_payload[0]
    if not isinstance(body, dict):
        return "internal_error", "Background create-from-image failed."

    error = body.get("error") or {}
    code = str(error.get("code") or "internal_error")
    message = str(error.get("message") or "Background create-from-image failed.")
    return code, message


def _refresh_bulk_ai_create_job_counters(db_session, job_id):
    counts_by_status = {
        BULK_AI_CREATE_ITEM_STATUS_COMPLETED: 0,
        BULK_AI_CREATE_ITEM_STATUS_FAILED: 0,
        BULK_AI_CREATE_ITEM_STATUS_RUNNING: 0,
        BULK_AI_CREATE_ITEM_STATUS_QUEUED: 0,
    }
    rows = db_session.execute(
        select(BulkAiCreateJobItem.status, func.count(BulkAiCreateJobItem.id))
        .where(BulkAiCreateJobItem.job_id == job_id)
        .group_by(BulkAiCreateJobItem.status)
    ).all()
    for status, count in rows:
        counts_by_status[str(status)] = int(count or 0)

    total_items = sum(counts_by_status.values())
    processed_items = counts_by_status[BULK_AI_CREATE_ITEM_STATUS_COMPLETED] + counts_by_status[BULK_AI_CREATE_ITEM_STATUS_FAILED]
    return {
        "total_items": total_items,
        "processed_items": processed_items,
        "succeeded_items": counts_by_status[BULK_AI_CREATE_ITEM_STATUS_COMPLETED],
        "failed_items": counts_by_status[BULK_AI_CREATE_ITEM_STATUS_FAILED],
        "remaining_items": counts_by_status[BULK_AI_CREATE_ITEM_STATUS_QUEUED] + counts_by_status[BULK_AI_CREATE_ITEM_STATUS_RUNNING],
    }


def _process_bulk_ai_create_job(app, job_id):
    with app.app_context():
        db_session = get_session()
        claimed = db_session.execute(
            sa_update(BulkAiCreateJob)
            .where(
                BulkAiCreateJob.id == int(job_id),
                BulkAiCreateJob.status == BULK_AI_CREATE_STATUS_QUEUED,
            )
            .values(
                status=BULK_AI_CREATE_STATUS_RUNNING,
                started_at=case(
                    (BulkAiCreateJob.started_at.is_(None), datetime.now(timezone.utc)),
                    else_=BulkAiCreateJob.started_at,
                ),
            )
        )
        db_session.commit()
        if int(claimed.rowcount or 0) == 0:
            return

        job = db_session.get(BulkAiCreateJob, int(job_id))
        if job is None:
            return

        actor_user = db_session.get(User, job.actor_user_id) if job.actor_user_id is not None else None
        actor_roles = _get_role_names_for_user_id(actor_user.id) if actor_user is not None else []

        if "administrator" not in actor_roles:
            job.status = BULK_AI_CREATE_STATUS_FAILED
            job.finished_at = datetime.now(timezone.utc)
            job.error_summary_json = json.dumps([
                {
                    "code": "forbidden",
                    "message": "Job actor does not have administrator role.",
                }
            ])
            db_session.commit()
            return

        items = db_session.execute(
            select(BulkAiCreateJobItem)
            .where(BulkAiCreateJobItem.job_id == job.id)
            .order_by(BulkAiCreateJobItem.id.asc())
        ).scalars().all()

        for item in items:
            if item.status in {BULK_AI_CREATE_ITEM_STATUS_COMPLETED, BULK_AI_CREATE_ITEM_STATUS_FAILED}:
                continue

            item.status = BULK_AI_CREATE_ITEM_STATUS_RUNNING
            item.attempts = int(item.attempts or 0) + 1
            db_session.commit()

            image_id = int(item.image_id or 0)
            response_payload = None
            if image_id <= 0:
                item.status = BULK_AI_CREATE_ITEM_STATUS_FAILED
                item.error_code = "not_found"
                item.error_message = "Image was not found."
                db_session.commit()
                continue

            request_id = f"job_{job.id}_{token_urlsafe(8)}"
            csrf_token = f"bulk_job_{token_urlsafe(8)}"
            with app.test_request_context(
                f"/api/v1/image-library/images/{image_id}/create-jigsaw",
                method="POST",
                json={},
                headers={"X-CSRF-Token": csrf_token},
            ):
                session["user_id"] = actor_user.id
                session["csrf_token"] = csrf_token
                g.request_id = request_id
                g.current_user = actor_user
                g.current_user_roles = actor_roles
                response_payload = create_jigsaw_from_image(image_id)

            status_code = _extract_response_status_code(response_payload)
            if 200 <= status_code < 300:
                item.status = BULK_AI_CREATE_ITEM_STATUS_COMPLETED
                item.error_code = None
                item.error_message = None
                image = db_session.get(JigsawImage, image_id)
                item.jigsaw_id = image.jigsaw_id if image is not None else None
            else:
                error_code, error_message = _extract_error_from_response(response_payload)
                item.status = BULK_AI_CREATE_ITEM_STATUS_FAILED
                item.error_code = error_code
                item.error_message = error_message
            db_session.commit()

        refreshed = _refresh_bulk_ai_create_job_counters(db_session, job.id)
        job.total_items = refreshed["total_items"]
        job.processed_items = refreshed["processed_items"]
        job.succeeded_items = refreshed["succeeded_items"]
        job.failed_items = refreshed["failed_items"]
        job.finished_at = datetime.now(timezone.utc)

        failed_items = db_session.execute(
            select(BulkAiCreateJobItem)
            .where(
                BulkAiCreateJobItem.job_id == job.id,
                BulkAiCreateJobItem.status == BULK_AI_CREATE_ITEM_STATUS_FAILED,
            )
            .order_by(BulkAiCreateJobItem.id.asc())
            .limit(20)
        ).scalars().all()
        job.error_summary_json = json.dumps(
            [
                {
                    "item_id": failed_item.id,
                    "image_id": failed_item.image_id,
                    "code": failed_item.error_code,
                    "message": failed_item.error_message,
                }
                for failed_item in failed_items
            ],
            sort_keys=True,
        )

        if refreshed["failed_items"] > 0:
            job.status = BULK_AI_CREATE_STATUS_FAILED
        else:
            job.status = BULK_AI_CREATE_STATUS_COMPLETED
        db_session.commit()


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
    role_names = sorted(roles)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "roles": role_names,
        "capabilities": _get_capabilities_for_roles(role_names),
    }


def _serialize_jigsaw(jigsaw):
    return {
        "id": jigsaw.id,
        "title": jigsaw.title,
        "series_name": jigsaw.series_name,
        "series_number": jigsaw.series_number,
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


def _normalize_image_content_version(value):
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 1
    return normalized if normalized > 0 else 1


def _build_image_urls(image_id, content_version):
    normalized_image_id = int(image_id)
    normalized_content_version = _normalize_image_content_version(content_version)
    version_query = f"v={normalized_content_version}"
    base_url = f"/api/v1/images/{normalized_image_id}/content"
    return {
        "content_url": f"{base_url}?{version_query}",
        "thumbnail_url": f"{base_url}?variant={IMAGE_VARIANT_THUMBNAIL}&{version_query}",
        "preview_url": f"{base_url}?variant={IMAGE_VARIANT_PREVIEW}&{version_query}",
    }


def _serialize_jigsaw_image(image):
    urls = _build_image_urls(image.id, getattr(image, "content_version", 1))
    return {
        "id": image.id,
        "jigsaw_id": image.jigsaw_id,
        "uploaded_by_user_id": image.uploaded_by_user_id,
        "tag": image.tag,
        "filename": image.filename,
        "mime_type": image.mime_type,
        "content_version": _normalize_image_content_version(getattr(image, "content_version", 1)),
        "content_url": urls["content_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "preview_url": urls["preview_url"],
        "captured_at": image.captured_at.isoformat() if image.captured_at else None,
        "captured_at_source": image.captured_at_source,
        "user_comment": image.user_comment,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


def _serialize_jigsaw_image_fields(
    *,
    image_id,
    jigsaw_id,
    tag,
    filename,
    mime_type,
    content_version,
    captured_at,
    captured_at_source,
    user_comment,
    created_at,
    uploaded_by_user_id=None,
):
    urls = _build_image_urls(image_id, content_version)
    return {
        "id": int(image_id),
        "jigsaw_id": jigsaw_id,
        "uploaded_by_user_id": uploaded_by_user_id,
        "tag": tag,
        "filename": filename,
        "mime_type": mime_type,
        "content_version": _normalize_image_content_version(content_version),
        "content_url": urls["content_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "preview_url": urls["preview_url"],
        "captured_at": captured_at.isoformat() if captured_at else None,
        "captured_at_source": captured_at_source,
        "user_comment": user_comment,
        "created_at": created_at.isoformat() if created_at else None,
    }


def _jigsaw_image_metadata_columns():
    return (
        JigsawImage.id,
        JigsawImage.jigsaw_id,
        JigsawImage.uploaded_by_user_id,
        JigsawImage.tag,
        JigsawImage.filename,
        JigsawImage.mime_type,
        JigsawImage.content_version,
        JigsawImage.captured_at,
        JigsawImage.captured_at_source,
        JigsawImage.user_comment,
        JigsawImage.created_at,
    )


def _jigsaw_thumbnail_tag_priority(tag):
    normalized = (tag or "").strip().lower()
    if normalized == IMAGE_BROWSER_TAG_BOX.lower():
        return 0
    if normalized == IMAGE_BROWSER_TAG_COMPLETED.lower():
        return 1
    return 2


def _serialize_diary_entry(entry):
    return {
        "id": entry.id,
        "jigsaw_id": entry.jigsaw_id,
        "created_by_user_id": entry.created_by_user_id,
        "updated_by_user_id": entry.updated_by_user_id,
        "source_image_id": entry.source_image_id,
        "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
        "difficulty": entry.difficulty,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _serialize_diary_feed_entry(*, entry, jigsaw_title=None, source_image=None):
    payload = _serialize_diary_entry(entry)
    payload["entry_type"] = "diary_entry"
    payload["jigsaw_title"] = jigsaw_title
    if isinstance(source_image, dict):
        payload["source_image"] = source_image
    elif source_image is not None:
        payload["source_image"] = _serialize_jigsaw_image(source_image)
    else:
        payload["source_image"] = None
    return payload


def _serialize_diary_feed_orphan_completed_image(image):
    if isinstance(image, dict):
        image_id = int(image.get("id") or 0)
        captured_at = image.get("captured_at")
        created_at = image.get("created_at")
        source_image_payload = image
    else:
        image_id = int(image.id)
        captured_at = image.captured_at
        created_at = image.created_at
        source_image_payload = _serialize_jigsaw_image(image)

    completed_at = captured_at or created_at

    def _to_iso(value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return value.isoformat()

    return {
        "entry_type": "orphan_completed_image",
        "id": image_id,
        "jigsaw_id": None,
        "jigsaw_title": None,
        "source_image_id": image_id,
        "completed_at": _to_iso(completed_at),
        "difficulty": None,
        "notes": None,
        "created_at": _to_iso(created_at),
        "updated_at": None,
        "source_image": source_image_payload,
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


def _serialize_blocked_ip(blocked_ip):
    now = datetime.now(timezone.utc)
    blocked_until = blocked_ip.blocked_until
    if blocked_until is not None and blocked_until.tzinfo is None:
        blocked_until = blocked_until.replace(tzinfo=timezone.utc)
    return {
        "id": blocked_ip.id,
        "ip_address": blocked_ip.ip_address,
        "blocked_until": blocked_until.isoformat() if blocked_until else None,
        "is_active": bool(blocked_until and blocked_until > now),
        "block_source": blocked_ip.block_source,
        "block_reason": blocked_ip.block_reason,
        "notes": blocked_ip.notes,
        "created_by_user_id": blocked_ip.created_by_user_id,
        "hit_count": int(blocked_ip.hit_count or 0),
        "created_at": blocked_ip.created_at.isoformat() if blocked_ip.created_at else None,
        "updated_at": blocked_ip.updated_at.isoformat() if blocked_ip.updated_at else None,
    }


def _deserialize_json_text(raw_text):
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text


def _serialize_ai_usage_event(event, image_filename=None, image_mime_type=None, image_size_bytes=None):
    provider_http_status = None
    if isinstance(event.error_message, str):
        match = re.search(r"HTTP\s+(\d{3})", event.error_message)
        if match is not None:
            try:
                provider_http_status = int(match.group(1))
            except ValueError:
                provider_http_status = None

    return {
        "id": event.id,
        "actor_user_id": event.actor_user_id,
        "image_id": event.image_id,
        "operation": event.operation,
        "status": event.status,
        "model": event.model,
        "endpoint_url": event.endpoint_url,
        "prompt_tokens": event.prompt_tokens,
        "completion_tokens": event.completion_tokens,
        "total_tokens": event.total_tokens,
        "provider_cost_usd": str(_to_decimal(event.provider_cost_usd) or Decimal("0")),
        "computed_cost_usd": str(_to_decimal(event.computed_cost_usd) or Decimal("0")),
        "final_cost_usd": str(_to_decimal(event.final_cost_usd) or Decimal("0")),
        "error_code": event.error_code,
        "error_message": event.error_message,
        "provider_http_status": provider_http_status,
        "request_id": event.request_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "payload": _deserialize_json_text(event.payload_json),
        "image": {
            "filename": image_filename,
            "mime_type": image_mime_type,
            "size_bytes": image_size_bytes,
        },
    }


def _build_ai_usage_window_summary(db_session, *, start_at, end_at):
    row = db_session.execute(
        select(
            func.count(AiUsageEvent.id),
            func.coalesce(func.sum(case((AiUsageEvent.status == AI_USAGE_STATUS_SUCCESS, 1), else_=0)), 0),
            func.coalesce(func.sum(AiUsageEvent.total_tokens), 0),
            func.coalesce(func.sum(AiUsageEvent.final_cost_usd), 0),
        ).where(AiUsageEvent.created_at >= start_at, AiUsageEvent.created_at < end_at)
    ).one()

    return {
        "calls": int(row[0] or 0),
        "success": int(row[1] or 0),
        "tokens": int(row[2] or 0),
        "cost_usd": str(_to_decimal(row[3]) or Decimal("0")),
    }


def _summarize_ai_usage_by_field(db_session, *, field_name, start_at, end_at):
    field = getattr(AiUsageEvent, field_name)
    rows = db_session.execute(
        select(
            field,
            func.count(AiUsageEvent.id),
            func.coalesce(func.sum(case((AiUsageEvent.status == AI_USAGE_STATUS_SUCCESS, 1), else_=0)), 0),
            func.coalesce(func.sum(AiUsageEvent.total_tokens), 0),
            func.coalesce(func.sum(AiUsageEvent.final_cost_usd), 0),
        )
        .where(AiUsageEvent.created_at >= start_at, AiUsageEvent.created_at < end_at)
        .group_by(field)
        .order_by(func.coalesce(func.sum(AiUsageEvent.final_cost_usd), 0).desc(), func.count(AiUsageEvent.id).desc())
    ).all()

    payload = []
    for group_value, calls, success, tokens, cost_usd in rows:
        payload.append(
            {
                field_name: group_value,
                "calls": int(calls or 0),
                "success": int(success or 0),
                "tokens": int(tokens or 0),
                "cost_usd": str(_to_decimal(cost_usd) or Decimal("0")),
            }
        )
    return payload


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


def _record_audit_event(action, entity_type, entity_id, payload=None, actor_user_id=None):
    db_session = get_session()

    audit_event = AuditEvent(
        actor_user_id=actor_user_id if actor_user_id is not None else getattr(g.current_user, "id", None),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        request_id=g.request_id,
        remote_addr=getattr(g, "remote_addr", request.remote_addr),
        client_ip_resolved=getattr(g, "client_ip_resolved", request.remote_addr),
        forwarded_chain=getattr(g, "forwarded_chain", None),
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


def _get_capabilities_for_roles(role_names):
    capabilities = set()
    for role_name in role_names or []:
        capabilities.update(ROLE_CAPABILITIES.get(str(role_name), set()))
    return sorted(capabilities)


def _current_user_has_capability(capability):
    if not capability:
        return False
    return capability in _get_capabilities_for_roles(getattr(g, "current_user_roles", []))


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


def _normalize_datetime_to_utc(value):
    if value is None or not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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


def _is_stfd_enabled():
    return bool(current_app.config.get("STFD_ENABLED", False))


def _normalize_stfd_uni(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip().strip('"').strip("'").strip().lower()
    if normalized.startswith("{") and normalized.endswith("}"):
        normalized = normalized[1:-1].strip().lower()
    return normalized


def _is_valid_absolute_http_url(value):
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    parsed = urllib.parse.urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _get_stfd_role_uni_by_name():
    return {
        "administrator": _normalize_stfd_uni(current_app.config.get("STFD_ROLE_UNI_ADMINISTRATOR", "") or ""),
        "member": _normalize_stfd_uni(current_app.config.get("STFD_ROLE_UNI_MEMBER", "") or ""),
        "borrower": _normalize_stfd_uni(current_app.config.get("STFD_ROLE_UNI_BORROWER", "") or ""),
    }


def _get_stfd_role_name_by_uni():
    role_uni_by_name = _get_stfd_role_uni_by_name()
    role_name_by_uni = {}
    for role_name, role_uni in role_uni_by_name.items():
        if role_uni:
            role_name_by_uni[role_uni] = role_name
    return role_name_by_uni


def _validate_stfd_runtime_config():
    app_uni = _normalize_stfd_uni(str(current_app.config.get("STFD_APP_UNI", "") or ""))
    shared_key = str(current_app.config.get("STFD_SHARED_KEY", "") or "").strip()
    assert_base_url = str(current_app.config.get("STFD_ASSERT_BASE_URL", "") or "").strip()
    redirect_uri = str(current_app.config.get("STFD_REDIRECT_URI", "") or "").strip()
    role_uni_by_name = _get_stfd_role_uni_by_name()

    if not app_uni:
        return None, _error_response("configuration_error", "STFD_APP_UNI is not configured.", 500)
    if not shared_key:
        return None, _error_response("configuration_error", "STFD_SHARED_KEY is not configured.", 500)
    if not assert_base_url:
        return None, _error_response("configuration_error", "STFD_ASSERT_BASE_URL is not configured.", 500)
    if not redirect_uri:
        return None, _error_response("configuration_error", "STFD_REDIRECT_URI is not configured.", 500)
    if not _is_valid_absolute_http_url(assert_base_url):
        return None, _error_response("configuration_error", "STFD_ASSERT_BASE_URL is invalid.", 500)
    if not _is_valid_absolute_http_url(redirect_uri):
        return None, _error_response("configuration_error", "STFD_REDIRECT_URI is invalid.", 500)

    missing_role_mappings = sorted([role_name for role_name, role_uni in role_uni_by_name.items() if not role_uni])
    if missing_role_mappings:
        return None, _error_response(
            "configuration_error",
            "STFD role UNI mapping is incomplete.",
            500,
            [{"field": "roles", "issue": f"missing UNI mapping for: {', '.join(missing_role_mappings)}"}],
        )

    return {
        "app_uni": app_uni,
        "shared_key": shared_key,
        "assert_base_url": assert_base_url,
        "redirect_uri": redirect_uri,
        "role_uni_by_name": role_uni_by_name,
        "role_name_by_uni": _get_stfd_role_name_by_uni(),
    }, None


def _sync_stfd_role_unis_from_config(db_session, role_uni_by_name):
    if not isinstance(role_uni_by_name, dict):
        return _error_response("configuration_error", "STFD role UNI mapping is invalid.", 500)

    role_names = list(role_uni_by_name.keys())
    roles = db_session.execute(select(Role).where(Role.name.in_(role_names))).scalars().all()
    roles_by_name = {role.name: role for role in roles}
    missing_roles = sorted([role_name for role_name in role_names if role_name not in roles_by_name])
    if missing_roles:
        return _error_response(
            "configuration_error",
            "One or more STFD-mapped roles do not exist in the local roles table.",
            500,
            [{"field": "roles", "issue": f"missing roles: {', '.join(missing_roles)}"}],
        )

    for role_name, expected_uni in role_uni_by_name.items():
        role = roles_by_name[role_name]
        current_uni = _normalize_stfd_uni(str(role.uni or ""))
        if not current_uni:
            role.uni = expected_uni
            continue
        if current_uni != expected_uni:
            return _error_response(
                "configuration_error",
                "Configured STFD role UNI does not match stored role UNI.",
                500,
                [{"field": "roles", "issue": f"role '{role_name}' has UNI '{role.uni}', expected '{expected_uni}'"}],
            )
        if role.uni != current_uni:
            role.uni = current_uni

    db_session.flush()

    return None


def _normalize_stfd_subject(raw_subject):
    if not isinstance(raw_subject, str) or not raw_subject.strip():
        return None
    subject = raw_subject.strip()
    if len(subject) > 255 or _contains_control_characters(subject):
        return None
    return subject


def _normalize_stfd_display_name(raw_display_name):
    if raw_display_name is None:
        return None
    if not isinstance(raw_display_name, str):
        return None
    display_name = raw_display_name.strip()
    if not display_name:
        return None
    if len(display_name) > DISPLAY_NAME_MAX_LENGTH:
        return None
    if _contains_control_characters(display_name) or "<" in display_name or ">" in display_name:
        return None
    return display_name


def _build_stfd_login_url(stfd_config):
    redirect_uri = urllib.parse.quote(stfd_config["redirect_uri"], safe="")
    app_uni = urllib.parse.quote(stfd_config["app_uni"], safe="")
    assert_base_url = stfd_config["assert_base_url"].rstrip("/")
    return f"{assert_base_url}/{app_uni}?redirect_uri={redirect_uri}"


def _auth_login_via_stfd_token(token):
    stfd_config, config_error = _validate_stfd_runtime_config()
    if config_error is not None:
        return config_error

    db_session = get_session()
    sync_error = _sync_stfd_role_unis_from_config(db_session, stfd_config["role_uni_by_name"])
    if sync_error is not None:
        db_session.rollback()
        return sync_error

    try:
        decoded = jwt.decode(
            token,
            stfd_config["shared_key"],
            algorithms=[STFD_JWT_ALGORITHM],
            options={"require": ["sub", "email", "app", "roles", "exp", "iat"]},
        )
    except jwt.InvalidTokenError:
        return _error_response("authentication_failed", "Invalid or expired STFD token.", 401)

    token_app_uni = str(decoded.get("app") or "").strip()
    if token_app_uni != stfd_config["app_uni"]:
        return _error_response("authentication_failed", "STFD token app UNI mismatch.", 401)

    auth_subject = _normalize_stfd_subject(decoded.get("sub"))
    if not auth_subject:
        return _error_response("authentication_failed", "STFD token subject is missing or invalid.", 401)

    email, email_error = _validate_email(decoded.get("email"), field_name="email")
    if email_error is not None:
        return _error_response("authentication_failed", "STFD token email is invalid.", 401)

    display_name = _normalize_stfd_display_name(decoded.get("friendly_name"))

    token_role_unis_raw = decoded.get("roles")
    if not isinstance(token_role_unis_raw, list) or len(token_role_unis_raw) == 0:
        return _error_response("forbidden", "No STFD roles were supplied for this application.", 403)

    token_role_unis = []
    for raw_role_uni in token_role_unis_raw:
        if not isinstance(raw_role_uni, str) or not raw_role_uni.strip():
            return _error_response("authentication_failed", "STFD token roles payload is invalid.", 401)
        normalized_role_uni = _normalize_stfd_uni(raw_role_uni)
        if not normalized_role_uni:
            return _error_response("authentication_failed", "STFD token roles payload is invalid.", 401)
        token_role_unis.append(normalized_role_uni)

    unique_role_unis = sorted(set(token_role_unis))
    roles = db_session.execute(select(Role).where(Role.uni.in_(unique_role_unis))).scalars().all()
    roles_by_uni = {str(role.uni): role for role in roles if role.uni}
    unknown_role_unis = sorted([role_uni for role_uni in unique_role_unis if role_uni not in roles_by_uni])
    if unknown_role_unis:
        return _error_response(
            "forbidden",
            "STFD token contains roles that are not mapped in this environment.",
            403,
            [{"field": "roles", "issue": f"unknown role UNI(s): {', '.join(unknown_role_unis)}"}],
        )

    target_roles = [roles_by_uni[role_uni] for role_uni in unique_role_unis]
    target_role_names = sorted([role.name for role in target_roles])

    user = db_session.execute(select(User).where(User.auth_subject == auth_subject)).scalar_one_or_none()
    was_created = False
    linked_by_email = False

    if user is None:
        existing_by_email = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing_by_email is not None:
            if existing_by_email.auth_subject and existing_by_email.auth_subject != auth_subject:
                return _error_response(
                    "conflict",
                    "This email is already linked to a different identity.",
                    409,
                )
            user = existing_by_email
            linked_by_email = True
        else:
            user = User(email=email, display_name=display_name, auth_subject=auth_subject, is_active=True)
            db_session.add(user)
            db_session.flush()
            was_created = True

    changed_fields = []
    if user.auth_subject != auth_subject:
        user.auth_subject = auth_subject
        changed_fields.append("auth_subject")
    if user.email != email:
        user.email = email
        changed_fields.append("email")
    if user.display_name != display_name:
        user.display_name = display_name
        changed_fields.append("display_name")
    if user.is_active is False:
        user.is_active = True
        changed_fields.append("is_active")

    current_role_rows = db_session.execute(select(UserRole.role_id).where(UserRole.user_id == user.id)).all()
    current_role_ids = {int(role_id) for (role_id,) in current_role_rows}
    target_role_ids = {int(role.id) for role in target_roles}
    roles_changed = current_role_ids != target_role_ids
    if roles_changed:
        db_session.execute(sa_delete(UserRole).where(UserRole.user_id == user.id))
        for role in target_roles:
            db_session.add(UserRole(user_id=user.id, role_id=role.id))

    csrf_token = token_urlsafe(24)
    session.clear()
    user_session = _create_user_session_record(db_session, user_id=user.id, auth_provider="stfd")
    session["user_id"] = user.id
    session["csrf_token"] = csrf_token
    session["auth_provider"] = "stfd"
    session[SESSION_IDENTIFIER_KEY] = user_session.session_identifier
    session.permanent = True
    g.current_user = user
    g.current_user_roles = target_role_names
    g.current_user_auth_provider = "stfd"

    if was_created:
        _record_audit_event(
            action="user.provisioned_from_stfd",
            entity_type="user",
            entity_id=user.id,
            payload={
                "auth_subject": auth_subject,
                "email": email,
                "roles": target_role_names,
            },
            actor_user_id=user.id,
        )
    elif changed_fields or roles_changed or linked_by_email:
        _record_audit_event(
            action="user.synced_from_stfd",
            entity_type="user",
            entity_id=user.id,
            payload={
                "changed_fields": sorted(changed_fields),
                "roles_changed": roles_changed,
                "roles": target_role_names,
                "linked_by_email": linked_by_email,
            },
            actor_user_id=user.id,
        )

    _record_audit_event(
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        payload={
            "auth_provider": "stfd",
            "auth_subject": auth_subject,
            "roles": target_role_names,
            "session_record_id": user_session.id,
        },
        actor_user_id=user.id,
    )
    db_session.commit()

    return _success_response(
        {
            "user": _serialize_user(user, target_role_names),
            "csrf_token": csrf_token,
            "auth_provider": "stfd",
            "session_identifier": user_session.session_identifier,
        }
    )


def _load_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    user_id = session.get("user_id")
    session_identifier = str(session.get(SESSION_IDENTIFIER_KEY) or "").strip()
    auth_provider = str(session.get("auth_provider") or "local").strip().lower() or "local"
    if user_id is None:
        g.current_user = None
        g.current_user_roles = []
        g.current_user_auth_provider = auth_provider
        return None

    db_session = get_session()
    user = db_session.get(User, user_id)
    if user is None or not user.is_active:
        session.clear()
        g.current_user = None
        g.current_user_roles = []
        g.current_user_auth_provider = auth_provider
        return None

    if not session_identifier:
        if bool(current_app.config.get("TESTING", False)):
            role_names = _get_role_names_for_user_id(user.id)
            g.current_user = user
            g.current_user_roles = role_names
            g.current_user_auth_provider = auth_provider
            return user

        session.clear()
        g.current_user = None
        g.current_user_roles = []
        g.current_user_auth_provider = auth_provider
        return None

    user_session = db_session.execute(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.session_identifier == session_identifier,
        )
    ).scalar_one_or_none()
    if user_session is None or user_session.terminated_at is not None:
        session.clear()
        g.current_user = None
        g.current_user_roles = []
        g.current_user_auth_provider = auth_provider
        return None

    now = datetime.now(timezone.utc)
    cutoff = _get_session_inactivity_cutoff(now)
    last_activity_at = _normalize_utc_datetime(user_session.last_activity_at)
    if last_activity_at is None or last_activity_at <= cutoff:
        _terminate_user_session_record(
            db_session,
            user_session,
            reason=SESSION_TERMINATION_REASON_EXPIRED,
            terminated_by_user_id=None,
        )
        db_session.commit()
        session.clear()
        g.current_user = None
        g.current_user_roles = []
        g.current_user_auth_provider = auth_provider
        return None

    should_touch_last_activity = (
        last_activity_at is None
        or (now - last_activity_at).total_seconds() >= SESSION_ACTIVITY_TOUCH_INTERVAL_SECONDS
    )
    if should_touch_last_activity:
        try:
            db_session.execute(
                sa_update(UserSession)
                .where(UserSession.id == user_session.id)
                .values(last_activity_at=now)
            )
            db_session.commit()
        except OperationalError:
            db_session.rollback()
            current_app.logger.warning(
                "user_session_touch_conflict",
                extra={
                    "session_id": user_session.id,
                    "user_id": user.id,
                    "request_id": getattr(g, "request_id", None),
                },
            )

    role_names = _get_role_names_for_user_id(user.id)

    g.current_user = user
    g.current_user_roles = role_names
    g.current_user_auth_provider = auth_provider
    return user


def _validate_csrf_for_request():
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None

    expected_token = session.get("csrf_token")
    provided_token = request.headers.get("X-CSRF-Token")
    if (
        not isinstance(expected_token, str)
        or not isinstance(provided_token, str)
        or not compare_digest(provided_token, expected_token)
    ):
        return _error_response("forbidden", "CSRF token is missing or invalid.", 403)

    return None


def _login_rate_limit_key(email):
    client_ip = str(getattr(g, "client_ip_resolved", request.remote_addr) or "unknown")
    return f"{client_ip}|{email}"


def _check_login_rate_limit(email):
    now = time.time()
    key = _login_rate_limit_key(email)
    with _failed_login_attempts_lock:
        state = _failed_login_attempts.get(key)
        if not state:
            return None

        blocked_until = float(state.get("blocked_until", 0) or 0)
        if blocked_until > now:
            retry_after_seconds = max(1, int(blocked_until - now))
            payload, status_code = _error_response(
                "too_many_requests",
                "Too many failed login attempts. Please try again later.",
                429,
            )
            return payload, status_code, retry_after_seconds

        window_started_at = float(state.get("window_started_at", 0) or 0)
        if window_started_at and now - window_started_at > LOGIN_RATE_LIMIT_WINDOW_SECONDS:
            _failed_login_attempts.pop(key, None)
    return None


def _record_failed_login_attempt(email):
    now = time.time()
    key = _login_rate_limit_key(email)
    should_persist_ip_block = False
    with _failed_login_attempts_lock:
        state = _failed_login_attempts.get(key)
        if not state or now - float(state.get("window_started_at", 0) or 0) > LOGIN_RATE_LIMIT_WINDOW_SECONDS:
            state = {"count": 0, "window_started_at": now, "blocked_until": 0}

        state["count"] = int(state.get("count", 0)) + 1
        if state["count"] >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
            state["blocked_until"] = now + LOGIN_RATE_LIMIT_BLOCK_SECONDS
            state["count"] = 0
            state["window_started_at"] = now
            should_persist_ip_block = True

        _failed_login_attempts[key] = state

    if should_persist_ip_block:
        _persist_failed_login_ip_block()


def _persist_failed_login_ip_block():
    client_ip = normalize_ip_address(getattr(g, "client_ip_resolved", request.remote_addr))
    if not client_ip:
        return

    db_session = get_session()
    try:
        blocked_until = datetime.now(timezone.utc) + timedelta(seconds=LOGIN_RATE_LIMIT_BLOCK_SECONDS)
        upsert_blocked_ip(
            db_session,
            ip_address=client_ip,
            blocked_until=blocked_until,
            block_source=LOGIN_RATE_LIMIT_BLOCK_SOURCE,
            block_reason="Repeated failed login attempts",
            created_by_user_id=None,
            add_hit=True,
            exempt_cidrs=current_app.config.get("TRUSTED_CLIENT_CIDRS", []),
        )
        db_session.commit()
    except ValueError:
        db_session.rollback()
    except Exception:
        db_session.rollback()
        current_app.logger.warning(
            "failed_login_ip_block_persist_failed",
            extra={
                "client_ip_resolved": client_ip,
                "request_id": getattr(g, "request_id", None),
            },
        )


def _clear_failed_login_attempts(email):
    key = _login_rate_limit_key(email)
    with _failed_login_attempts_lock:
        _failed_login_attempts.pop(key, None)


def reset_runtime_security_state():
    with _failed_login_attempts_lock:
        _failed_login_attempts.clear()


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


def _parse_required_positive_integer_or_null(value, field_name):
    if value is None:
        return None, None

    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": field_name, "issue": "must be a positive integer or null"}],
        )

    return value, None


def _parse_list_pagination_query(*, default_page_size, max_page_size, legacy_limit_max=None):
    raw_page = request.args.get("page")
    raw_page_size = request.args.get("page_size")
    raw_limit = request.args.get("limit")

    if raw_page is None:
        page = 1
    else:
        try:
            page = int(raw_page)
        except ValueError:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "page", "issue": "must be an integer"}],
            )
        if page < 1:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "page", "issue": "must be greater than or equal to 1"}],
            )

    if raw_page_size is not None:
        try:
            page_size = int(raw_page_size)
        except ValueError:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "page_size", "issue": "must be an integer"}],
            )
        if page_size < 1 or page_size > max_page_size:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "page_size", "issue": f"must be between 1 and {max_page_size}"}],
            )
    elif raw_limit is not None:
        try:
            page_size = int(raw_limit)
        except ValueError:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "limit", "issue": "must be an integer"}],
            )

        effective_legacy_limit_max = legacy_limit_max if legacy_limit_max is not None else max_page_size
        if page_size < 1 or page_size > effective_legacy_limit_max:
            return None, _error_response(
                "validation_error",
                "Invalid request query.",
                422,
                [{"field": "limit", "issue": f"must be between 1 and {effective_legacy_limit_max}"}],
            )
    else:
        page_size = default_page_size

    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
    }, None


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


def _is_allowed_image_mime_type(mime_type):
    normalized = str(mime_type or "").strip().lower()
    return normalized in ALLOWED_RASTER_IMAGE_MIME_TYPES


def _is_truthy_form_value(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


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


def _parse_exif_datetime_value(value):
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return None

    if not isinstance(value, str):
        return None

    stripped = value.replace("\x00", "").strip()
    if not stripped:
        return None

    exif_pattern = re.compile(
        r"^(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(?:\s*(Z|[+-]\d{2}:?\d{2}))?$"
    )
    match = exif_pattern.match(stripped)
    if match:
        year, month, day, hour, minute, second, fractional, offset_text = match.groups()
        microsecond = int((fractional or "0").ljust(6, "0")[:6])
        parsed = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            microsecond,
        )
        if offset_text:
            if offset_text == "Z":
                return parsed.replace(tzinfo=timezone.utc).astimezone(timezone.utc)
            normalized_offset = offset_text.replace(":", "")
            sign = 1 if normalized_offset[0] == "+" else -1
            offset_hours = int(normalized_offset[1:3])
            offset_minutes = int(normalized_offset[3:5])
            offset_delta = timedelta(hours=offset_hours, minutes=offset_minutes)
            tz = timezone(sign * offset_delta)
            return parsed.replace(tzinfo=tz).astimezone(timezone.utc)
        return parsed.replace(tzinfo=timezone.utc)

    for fmt in (
        "%Y:%m:%d %H:%M:%S",
        "%Y:%m:%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            parsed = datetime.strptime(stripped, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_image_captured_at(image_data):
    if Image is None:
        return None, None, None

    try:
        with Image.open(BytesIO(image_data)) as image_file:
            exif = image_file.getexif()
            info_items = dict(image_file.info or {})
    except (UnidentifiedImageError, OSError, ValueError):
        return None, None, None

    if not exif:
        return None, None, None

    date_tag_candidates = (
        (36867, "exif_datetime_original"),
        (36868, "exif_datetime_digitized"),
        (306, "exif_datetime"),
    )
    for tag_id, source in date_tag_candidates:
        raw_value = exif.get(tag_id)
        parsed = _parse_exif_datetime_value(raw_value)
        if parsed is not None:
            raw_text = raw_value.decode("utf-8", errors="ignore") if isinstance(raw_value, bytes) else str(raw_value)
            return parsed, source, raw_text[:64]

    info_date_candidates = (
        ("creation_time", "image_info_creation_time"),
        ("Creation Time", "image_info_creation_time"),
        ("date:create", "image_info_date_create"),
        ("date:modify", "image_info_date_modify"),
    )
    for key, source in info_date_candidates:
        raw_value = info_items.get(key)
        parsed = _parse_exif_datetime_value(raw_value)
        if parsed is not None:
            raw_text = raw_value.decode("utf-8", errors="ignore") if isinstance(raw_value, bytes) else str(raw_value)
            return parsed, source, raw_text[:64]

    return None, None, None


def _backfill_image_capture_metadata(image, captured_at, captured_at_source, captured_at_raw):
    if captured_at is None or image.captured_at is not None:
        return False
    image.captured_at = captured_at
    image.captured_at_source = captured_at_source
    image.captured_at_raw = captured_at_raw
    return True


def _backfill_image_user_comment(image, user_comment):
    comment = str(user_comment or "").strip()
    if not comment:
        return False
    if str(image.user_comment or "").strip():
        return False
    image.user_comment = comment
    return True


def _backfill_image_uploaded_by(image, uploaded_by_user_id):
    if uploaded_by_user_id is None:
        return False
    if image.uploaded_by_user_id is not None:
        return False
    image.uploaded_by_user_id = int(uploaded_by_user_id)
    return True


def _refresh_image_embedding_for_image_id(app, image_id):
    with app.app_context():
        if not bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False)):
            return

        db_session = get_session()
        model_name, model_revision, model_key, model_local_path, local_files_only = _get_embedding_model_config()
        allow_test_fallback = _allow_image_embeddings_test_fallback()
        refreshed = _refresh_image_embedding_with_retry(
            db_session,
            image_id=int(image_id),
            model_name=model_name,
            model_revision=model_revision,
            model_key=model_key,
            model_local_path=model_local_path,
            local_files_only=local_files_only,
            allow_test_fallback=allow_test_fallback,
        )
        if refreshed is not None:
            db_session.commit()


def _queue_image_embedding_refresh(image_id):
    if not bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False)):
        return

    runtime_error = embedding_runtime_error()
    if runtime_error is not None and not _allow_image_embeddings_test_fallback():
        current_app.logger.warning(
            "image_embedding_refresh_skipped_runtime_unavailable",
            extra={"image_id": int(image_id), "error": runtime_error},
        )
        return

    app = current_app._get_current_object()
    if bool(current_app.config.get("TESTING", False)) and bool(current_app.config.get("IMAGE_EMBEDDINGS_INLINE", False)):
        _refresh_image_embedding_for_image_id(app, int(image_id))
        return

    worker = threading.Thread(
        target=_run_image_embedding_refresh,
        args=(app, int(image_id)),
        name=f"image-embedding-refresh-{int(image_id)}",
        daemon=True,
    )
    worker.start()


def _run_image_embedding_refresh(app, image_id):
    try:
        _refresh_image_embedding_for_image_id(app, int(image_id))
    except Exception:
        app.logger.exception("image_embedding_refresh_failed", extra={"image_id": int(image_id)})


def _refresh_image_derivatives_for_image_id(app, image_id):
    with app.app_context():
        db_session = get_session()
        image = db_session.get(JigsawImage, int(image_id))
        if image is None:
            return

        had_missing_derivatives = image.thumbnail_data is None or image.preview_data is None
        variants = _build_image_variants(image.image_data, image.mime_type)
        image.thumbnail_mime_type = variants["thumbnail_mime_type"]
        image.thumbnail_data = variants["thumbnail_data"]
        image.preview_mime_type = variants["preview_mime_type"]
        image.preview_data = variants["preview_data"]
        if had_missing_derivatives:
            image.content_version = _normalize_image_content_version(getattr(image, "content_version", 1)) + 1

        if image.captured_at is None:
            captured_at, captured_at_source, captured_at_raw = _extract_image_captured_at(image.image_data)
            if captured_at is not None:
                image.captured_at = captured_at
                image.captured_at_source = captured_at_source
                image.captured_at_raw = captured_at_raw

        db_session.commit()


def _queue_image_derivatives_refresh(image_id):
    app = current_app._get_current_object()
    if bool(current_app.config.get("TESTING", False)):
        _refresh_image_derivatives_for_image_id(app, int(image_id))
        return

    worker = threading.Thread(
        target=_refresh_image_derivatives_for_image_id,
        args=(app, int(image_id)),
        name=f"image-derivatives-refresh-{int(image_id)}",
        daemon=True,
    )
    worker.start()


def _is_completed_image_tag(tag_value):
    normalized = str(tag_value or "").strip().lower()
    if not normalized:
        return False
    if normalized == IMAGE_BROWSER_TAG_COMPLETED.lower():
        return True
    normalized = normalized.replace("_", " ").replace("-", " ")
    return normalized.startswith("completed") or normalized.startswith("complete")


def _is_reference_image_tag(tag_value):
    normalized = str(tag_value or "").strip().lower().replace("_", " ").replace("-", " ")
    if not normalized:
        return False
    prefixes = _reference_tag_prefixes()
    return any(normalized.startswith(prefix) for prefix in prefixes)


def _reference_tag_prefixes():
    configured_prefixes = current_app.config.get("IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES") or []
    prefixes = [str(value).strip().lower() for value in configured_prefixes if str(value or "").strip()]
    if not prefixes:
        prefixes = ["box", "reference"]
    return prefixes


def _build_reference_tag_sql_filter(column):
    prefixes = _reference_tag_prefixes()
    clauses = [func.lower(func.coalesce(column, "")).like(f"{prefix}%") for prefix in prefixes]
    if not clauses:
        return None
    return or_(*clauses)


def _parse_embedding_vector(raw_vector_json):
    if not isinstance(raw_vector_json, str) or not raw_vector_json.strip():
        return None
    try:
        parsed = json.loads(raw_vector_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    values = []
    for item in parsed:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            return None
    return values


def _compute_percentile(values, percentile):
    if not values:
        return None
    ordered = sorted(int(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = int(round((len(ordered) - 1) * float(percentile)))
    rank = max(0, min(rank, len(ordered) - 1))
    return ordered[rank]


def _build_image_embedding_diagnostics_payload(db_session, *, missing_preview_limit=24):
    model_name, model_revision, model_key, model_local_path, local_files_only = _get_embedding_model_config()

    image_rows = db_session.execute(
        select(
            JigsawImage.id,
            JigsawImage.jigsaw_id,
            JigsawImage.uploaded_by_user_id,
            JigsawImage.tag,
            JigsawImage.filename,
            JigsawImage.mime_type,
            JigsawImage.content_version,
            JigsawImage.captured_at,
            JigsawImage.captured_at_source,
            JigsawImage.user_comment,
            JigsawImage.created_at,
            JigsawImage.image_data,
            ImageEmbedding.source_content_sha256,
        )
        .select_from(JigsawImage)
        .outerjoin(
            ImageEmbedding,
            (ImageEmbedding.image_id == JigsawImage.id) & (ImageEmbedding.model_key == model_key),
        )
        .order_by(JigsawImage.id.asc())
    ).all()

    total_images = len(image_rows)
    up_to_date = 0
    stale = 0
    missing = 0
    missing_images = []

    for (
        image_id,
        jigsaw_id,
        uploaded_by_user_id,
        tag,
        filename,
        mime_type,
        content_version,
        captured_at,
        captured_at_source,
        user_comment,
        created_at,
        image_data,
        source_content_sha256,
    ) in image_rows:
        if not source_content_sha256:
            missing += 1
            if len(missing_images) < int(max(1, min(200, missing_preview_limit))):
                missing_images.append(
                    _serialize_jigsaw_image_fields(
                        image_id=image_id,
                        jigsaw_id=jigsaw_id,
                        uploaded_by_user_id=uploaded_by_user_id,
                        tag=tag,
                        filename=filename,
                        mime_type=mime_type,
                        content_version=content_version,
                        captured_at=captured_at,
                        captured_at_source=captured_at_source,
                        user_comment=user_comment,
                        created_at=created_at,
                    )
                )
            continue
        computed_sha = compute_content_sha256(image_data)
        if compare_digest(str(source_content_sha256), computed_sha):
            up_to_date += 1
        else:
            stale += 1

    duration_values = [
        int(value)
        for value in db_session.execute(
            select(ImageEmbedding.compute_duration_ms)
            .where(
                ImageEmbedding.model_key == model_key,
                ImageEmbedding.compute_duration_ms.is_not(None),
            )
            .order_by(ImageEmbedding.id.asc())
        ).scalars().all()
        if value is not None
    ]

    latest_job = db_session.execute(
        select(ImageEmbeddingJob).where(ImageEmbeddingJob.model_key == model_key).order_by(ImageEmbeddingJob.id.desc()).limit(1)
    ).scalar_one_or_none()

    return {
        "model": {
            "name": model_name,
            "revision": model_revision,
            "model_key": model_key,
            "local_path": model_local_path or None,
            "local_files_only": local_files_only,
        },
        "health": {
            "total_images": total_images,
            "up_to_date_embeddings": up_to_date,
            "stale_embeddings": stale,
            "missing_embeddings": missing,
            "all_images_up_to_date": total_images == up_to_date,
        },
        "missing_images": missing_images,
        "performance": {
            "samples": len(duration_values),
            "min_ms": min(duration_values) if duration_values else None,
            "avg_ms": int(round(sum(duration_values) / len(duration_values))) if duration_values else None,
            "p95_ms": _compute_percentile(duration_values, 0.95),
            "max_ms": max(duration_values) if duration_values else None,
        },
        "latest_backfill_job": _serialize_image_embedding_job(latest_job) if latest_job is not None else None,
    }


def _normalize_utc_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize_user_session(user_session, user):
    return {
        "id": user_session.id,
        "session_identifier": user_session.session_identifier,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
        }
        if user is not None
        else None,
        "origin_ip_address": user_session.origin_ip_address,
        "auth_provider": user_session.auth_provider,
        "created_at": _normalize_utc_datetime(user_session.created_at).isoformat() if user_session.created_at else None,
        "last_activity_at": _normalize_utc_datetime(user_session.last_activity_at).isoformat()
        if user_session.last_activity_at
        else None,
    }


def _serialize_database_backup(database_backup):
    status = str(database_backup.status or "").strip().lower()
    is_downloadable = status == DATABASE_BACKUP_STATUS_COMPLETED
    filename = str(database_backup.filename or "")
    compression = BACKUP_COMPRESSION_NONE
    if filename.endswith(".sql.gz"):
        compression = BACKUP_COMPRESSION_GZIP
    elif filename.endswith(".sql.bz2"):
        compression = BACKUP_COMPRESSION_BZIP2
    return {
        "id": database_backup.id,
        "initiated_by_user_id": database_backup.initiated_by_user_id,
        "filename": filename,
        "file_format": database_backup.file_format,
        "compression": compression,
        "status": status,
        "app_environment": database_backup.app_environment,
        "app_environment_label": normalize_environment_label(database_backup.app_environment),
        "app_version": database_backup.app_version,
        "file_size_bytes": int(database_backup.file_size_bytes) if database_backup.file_size_bytes is not None else None,
        "file_sha256": database_backup.file_sha256,
        "error_message": database_backup.error_message,
        "created_at": _normalize_utc_datetime(database_backup.created_at).isoformat() if database_backup.created_at else None,
        "started_at": _normalize_utc_datetime(database_backup.started_at).isoformat() if database_backup.started_at else None,
        "completed_at": _normalize_utc_datetime(database_backup.completed_at).isoformat()
        if database_backup.completed_at
        else None,
        "download_url": f"/api/v1/system/database-backups/{database_backup.id}/download" if is_downloadable else None,
        "delete_url": f"/api/v1/system/database-backups/{database_backup.id}",
    }


def _resolve_database_backup_root_path():
    return resolve_backup_root_path(
        app_instance_path=current_app.instance_path,
        configured_path=current_app.config.get("DB_BACKUP_STORAGE_PATH", ""),
    )


def _resolve_database_backup_file_path(backup_record):
    backup_root = _resolve_database_backup_root_path()
    candidate_path = Path(str(backup_record.storage_path or "")).resolve()
    if backup_root != candidate_path and backup_root not in candidate_path.parents:
        raise RuntimeError("Backup storage path is outside the configured backup root.")
    return candidate_path


def _resolve_database_backup_compression():
    configured = str(current_app.config.get("DB_BACKUP_COMPRESSION", BACKUP_COMPRESSION_GZIP) or "")
    return normalize_backup_compression(configured, default=BACKUP_COMPRESSION_GZIP)


def _resolve_database_backup_mime_type(filename):
    normalized = str(filename or "").strip().lower()
    if normalized.endswith(".sql.gz"):
        return "application/gzip"
    if normalized.endswith(".sql.bz2"):
        return "application/x-bzip2"
    return "application/sql"


def _build_unique_backup_filename(*, backup_root, generated_at, app_env, app_version, compression):
    base_filename = build_backup_filename(
        app_name=DEFAULT_BACKUP_APP_NAME,
        app_env=app_env,
        app_version=app_version,
        generated_at=generated_at,
        compression=compression,
    )
    candidate_filename = base_filename
    suffix = 1
    while (backup_root / candidate_filename).exists():
        if base_filename.endswith(".sql.gz"):
            candidate_filename = base_filename[: -len(".sql.gz")] + f"-{suffix}.sql.gz"
        elif base_filename.endswith(".sql.bz2"):
            candidate_filename = base_filename[: -len(".sql.bz2")] + f"-{suffix}.sql.bz2"
        else:
            candidate_filename = base_filename[: -len(".sql")] + f"-{suffix}.sql"
        suffix += 1
    return candidate_filename


def _execute_database_backup_job(app, backup_id):
    with app.app_context():
        db_session = get_session()
        backup_record = db_session.get(DatabaseBackup, int(backup_id))
        if backup_record is None:
            db_session.remove()
            return

        started_at = datetime.now(timezone.utc)
        backup_record.status = DATABASE_BACKUP_STATUS_RUNNING
        backup_record.started_at = started_at
        backup_record.completed_at = None
        backup_record.file_size_bytes = None
        backup_record.file_sha256 = None
        backup_record.error_message = None
        db_session.commit()

        try:
            backup_path = _resolve_database_backup_file_path(backup_record)
            backup_root = _resolve_database_backup_root_path()
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_compression = _resolve_database_backup_compression()

            backup_sql = build_mysql_compatible_backup_sql(
                engine=db_session.get_bind(),
                app_name=DEFAULT_BACKUP_APP_NAME,
                app_env=backup_record.app_environment,
                app_version=backup_record.app_version,
                generated_at=started_at,
                blob_chunk_bytes=int(current_app.config.get("DB_BACKUP_BLOB_CHUNK_BYTES", 32 * 1024) or 32 * 1024),
                max_statement_bytes=int(
                    current_app.config.get("DB_BACKUP_MAX_STATEMENT_BYTES", 4 * 1024 * 1024) or (4 * 1024 * 1024)
                ),
            )
            encoded_sql = backup_sql.encode("utf-8")
            backup_bytes = compress_backup_payload(encoded_sql, compression=backup_compression)
            sql_sha = hashlib.sha256(backup_bytes).hexdigest()

            temp_path = backup_path.with_suffix(backup_path.suffix + ".tmp")
            with temp_path.open("wb") as backup_stream:
                backup_stream.write(backup_bytes)
            temp_path.replace(backup_path)

            backup_record.status = DATABASE_BACKUP_STATUS_COMPLETED
            backup_record.completed_at = datetime.now(timezone.utc)
            backup_record.file_size_bytes = int(len(backup_bytes))
            backup_record.file_sha256 = sql_sha
            backup_record.error_message = None
            db_session.add(
                AuditEvent(
                    actor_user_id=backup_record.initiated_by_user_id,
                    action="system.database_backup_completed",
                    entity_type="database_backup",
                    entity_id=str(backup_record.id),
                    request_id=None,
                    remote_addr=None,
                    client_ip_resolved=None,
                    forwarded_chain=None,
                    scheme=None,
                    host=None,
                    payload_json=json.dumps(
                        {
                            "filename": backup_record.filename,
                            "file_size_bytes": backup_record.file_size_bytes,
                            "file_sha256": backup_record.file_sha256,
                        },
                        sort_keys=True,
                    ),
                )
            )
            db_session.commit()
        except Exception as error:
            backup_record.status = DATABASE_BACKUP_STATUS_FAILED
            backup_record.completed_at = datetime.now(timezone.utc)
            backup_record.error_message = str(error)[:2000]
            db_session.add(
                AuditEvent(
                    actor_user_id=backup_record.initiated_by_user_id,
                    action="system.database_backup_failed",
                    entity_type="database_backup",
                    entity_id=str(backup_record.id),
                    request_id=None,
                    remote_addr=None,
                    client_ip_resolved=None,
                    forwarded_chain=None,
                    scheme=None,
                    host=None,
                    payload_json=json.dumps(
                        {
                            "filename": backup_record.filename,
                            "error_message": backup_record.error_message,
                        },
                        sort_keys=True,
                    ),
                )
            )
            db_session.commit()
        finally:
            db_session.remove()


def _start_database_backup_job(backup_id):
    app = current_app._get_current_object()
    worker = threading.Thread(
        target=_execute_database_backup_job,
        args=(app, int(backup_id)),
        daemon=True,
        name=f"database-backup-{int(backup_id)}",
    )
    worker.start()


def _get_session_inactivity_cutoff(now=None):
    resolved_now = now or datetime.now(timezone.utc)
    timeout_minutes = int(current_app.config.get("SESSION_IDLE_TIMEOUT_MINUTES", 120) or 120)
    if timeout_minutes < 1:
        timeout_minutes = 120
    return resolved_now - timedelta(minutes=timeout_minutes)


def _create_user_session_record(db_session, *, user_id, auth_provider):
    now = datetime.now(timezone.utc)
    user_session = UserSession(
        user_id=user_id,
        session_identifier=token_urlsafe(32),
        origin_ip_address=getattr(g, "client_ip_resolved", request.remote_addr),
        auth_provider=str(auth_provider or "local").strip().lower() or "local",
        created_at=now,
        last_activity_at=now,
    )
    db_session.add(user_session)
    db_session.flush()
    return user_session


def _terminate_user_session_record(db_session, user_session, *, reason, terminated_by_user_id=None):
    if user_session is None:
        return False
    if user_session.terminated_at is not None:
        return False
    user_session.terminated_at = datetime.now(timezone.utc)
    user_session.termination_reason = str(reason or "terminated").strip()[:64] or "terminated"
    user_session.terminated_by_user_id = terminated_by_user_id
    db_session.flush()
    return True


def _maybe_create_diary_entry_from_image(*, db_session, jigsaw, image, trigger, created_by_user_id):
    if jigsaw is None or image is None:
        return None
    if image.jigsaw_id != jigsaw.id:
        return None
    if not _is_completed_image_tag(image.tag):
        return None

    existing_entry = db_session.execute(
        select(JigsawDiaryEntry.id).where(JigsawDiaryEntry.source_image_id == image.id).limit(1)
    ).scalar_one_or_none()
    if existing_entry is not None:
        return None

    completed_at = _normalize_datetime_to_utc(image.captured_at) or datetime.now(timezone.utc)
    source_label = "image_exif" if image.captured_at is not None else "fallback_now"
    default_notes = f"Auto-created from completed image ({source_label})."
    comment = str(image.user_comment or "").strip()
    if comment:
        notes = comment
    else:
        notes = default_notes

    entry = JigsawDiaryEntry(
        jigsaw_id=jigsaw.id,
        created_by_user_id=int(created_by_user_id),
        source_image_id=image.id,
        completed_at=completed_at,
        difficulty=None,
        notes=notes,
    )
    db_session.add(entry)
    db_session.flush()

    existing_last_completed_at = _normalize_datetime_to_utc(jigsaw.last_completed_at)
    if existing_last_completed_at is None or completed_at > existing_last_completed_at:
        jigsaw.last_completed_at = completed_at

    _record_audit_event(
        action="jigsaw.diary_entry_created_from_image",
        entity_type="jigsaw_diary_entry",
        entity_id=entry.id,
        payload={
            "jigsaw_id": jigsaw.id,
            "image_id": image.id,
            "trigger": trigger,
            "completed_at": completed_at.isoformat(),
            "captured_at_source": image.captured_at_source,
        },
    )
    return entry


def _recompute_jigsaw_last_completed_at(db_session, jigsaw):
    if jigsaw is None:
        return

    latest_completed_at = db_session.execute(
        select(func.max(JigsawDiaryEntry.completed_at)).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id)
    ).scalar_one()
    jigsaw.last_completed_at = latest_completed_at


def _create_jigsaw_image_record(
    db_session,
    *,
    jigsaw_id,
    tag,
    filename,
    mime_type,
    image_data,
    image_sha256,
    captured_at=None,
    captured_at_source=None,
    captured_at_raw=None,
    user_comment=None,
    uploaded_by_user_id=None,
    variants=None,
):
    if variants is None:
        variants = _build_image_variants(image_data, mime_type)
    image = JigsawImage(
        jigsaw_id=jigsaw_id,
        tag=tag,
        filename=filename,
        mime_type=mime_type,
        image_data=image_data,
        thumbnail_mime_type=variants["thumbnail_mime_type"],
        thumbnail_data=variants["thumbnail_data"],
        preview_mime_type=variants["preview_mime_type"],
        preview_data=variants["preview_data"],
        image_sha256=image_sha256,
        content_version=1,
        captured_at=captured_at,
        captured_at_source=captured_at_source,
        captured_at_raw=captured_at_raw,
        user_comment=user_comment,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db_session.add(image)
    db_session.flush()
    return image


def _extract_zip_image_items(upload):
    issues = []
    images = []
    total_uncompressed_bytes = 0

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
                if not _is_allowed_image_mime_type(mime_type):
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

                total_uncompressed_bytes += int(entry.file_size or 0)
                if total_uncompressed_bytes > (JIGSAW_IMAGE_MAX_BYTES * 20):
                    issues.append(
                        {
                            "filename": filename,
                            "issue": "zip archive contains too much uncompressed image data",
                        }
                    )
                    break

                compressed_size = int(entry.compress_size or 0)
                if compressed_size > 0:
                    compression_ratio = float(entry.file_size) / float(compressed_size)
                    if compression_ratio > 100:
                        issues.append(
                            {
                                "filename": filename,
                                "issue": "zip entry compression ratio is too high",
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

                captured_at, captured_at_source, captured_at_raw = _extract_image_captured_at(image_data)

                images.append(
                    {
                        "filename": normalized_filename,
                        "mime_type": mime_type,
                        "image_data": image_data,
                        "image_sha256": _compute_image_sha256(image_data),
                        "captured_at": captured_at,
                        "captured_at_source": captured_at_source,
                        "captured_at_raw": captured_at_raw,
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
        if not _is_allowed_image_mime_type(mime_type):
            issues.append(
                {
                    "filename": upload.filename or "(unnamed)",
                    "issue": "must be a supported image type or zip file",
                }
            )
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

        captured_at, captured_at_source, captured_at_raw = _extract_image_captured_at(image_data)

        image_items.append(
            {
                "filename": filename,
                "mime_type": mime_type,
                "image_data": image_data,
                "image_sha256": _compute_image_sha256(image_data),
                "captured_at": captured_at,
                "captured_at_source": captured_at_source,
                "captured_at_raw": captured_at_raw,
                "source": upload.filename or "(unnamed)",
            }
        )

    return image_items, issues


def _resize_image_for_width(image, target_width):
    if target_width <= 0:
        return image.copy()

    width = max(1, int(image.width))
    height = max(1, int(image.height))
    if width <= target_width:
        return image.copy()

    ratio = target_width / float(width)
    next_size = (target_width, max(1, int(round(height * ratio))))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    return image.resize(next_size, resampling)


def _encode_variant_image(image):
    has_alpha = "A" in image.getbands() or image.mode in {"LA", "RGBA", "PA"}
    output_buffer = BytesIO()
    if has_alpha:
        encoded = image.convert("RGBA")
        encoded.save(output_buffer, format="PNG", optimize=True)
        return "image/png", output_buffer.getvalue()

    encoded = image.convert("RGB")
    encoded.save(output_buffer, format="JPEG", quality=82, optimize=True, progressive=True)
    return "image/jpeg", output_buffer.getvalue()


def _build_image_variants(image_data, mime_type):
    fallback = {
        "thumbnail_mime_type": mime_type,
        "thumbnail_data": image_data,
        "preview_mime_type": mime_type,
        "preview_data": image_data,
    }
    if Image is None or ImageOps is None:
        return fallback

    try:
        with Image.open(BytesIO(image_data)) as source_image:
            normalized = ImageOps.exif_transpose(source_image)
            thumbnail_image = _resize_image_for_width(normalized, THUMBNAIL_TARGET_WIDTH)
            preview_image = _resize_image_for_width(normalized, PREVIEW_TARGET_WIDTH)
            thumbnail_mime_type, thumbnail_data = _encode_variant_image(thumbnail_image)
            preview_mime_type, preview_data = _encode_variant_image(preview_image)
    except (UnidentifiedImageError, DecompressionBombError, OSError, ValueError):
        return fallback

    return {
        "thumbnail_mime_type": thumbnail_mime_type,
        "thumbnail_data": thumbnail_data,
        "preview_mime_type": preview_mime_type,
        "preview_data": preview_data,
    }


def _resolve_image_variant_payload(image, variant):
    if variant == IMAGE_VARIANT_THUMBNAIL:
        return image.thumbnail_data or image.image_data, image.thumbnail_mime_type or image.mime_type
    if variant == IMAGE_VARIANT_PREVIEW:
        return image.preview_data or image.image_data, image.preview_mime_type or image.mime_type
    return image.image_data, image.mime_type


def _variant_has_derived_payload(image, variant):
    if variant == IMAGE_VARIANT_THUMBNAIL:
        return bool(image.thumbnail_data)
    if variant == IMAGE_VARIANT_PREVIEW:
        return bool(image.preview_data)
    return True


def _requested_image_content_version_matches(image, raw_version):
    if raw_version is None:
        return False
    try:
        requested_version = int(str(raw_version).strip())
    except (TypeError, ValueError):
        return False
    return requested_version > 0 and requested_version == _normalize_image_content_version(getattr(image, "content_version", 1))


def _build_image_content_response(image, variant):
    image_bytes, mime_type = _resolve_image_variant_payload(image, variant)
    response = current_app.response_class(image_bytes, mimetype=mime_type)
    has_derived_payload = _variant_has_derived_payload(image, variant)
    has_versioned_request = _requested_image_content_version_matches(image, request.args.get("v"))
    if has_versioned_request and has_derived_payload:
        response.headers["Cache-Control"] = "private, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-store"
    if variant != IMAGE_VARIANT_ORIGINAL:
        response.headers["Vary"] = "Accept"
    response.set_etag(f'img-{int(image.id)}-{variant}-v{_normalize_image_content_version(getattr(image, "content_version", 1))}')
    response.make_conditional(request)
    if image.filename and variant == IMAGE_VARIANT_ORIGINAL:
        response.headers["Content-Disposition"] = f'inline; filename="{image.filename}"'
    return response


def _compute_image_sha256(image_data):
    return hashlib.sha256(image_data).hexdigest()


def _parse_image_variant(raw_variant):
    if raw_variant is None:
        return IMAGE_VARIANT_ORIGINAL, None
    normalized = str(raw_variant).strip().lower()
    if not normalized:
        return IMAGE_VARIANT_ORIGINAL, None
    aliases = {
        "content": IMAGE_VARIANT_ORIGINAL,
        "full": IMAGE_VARIANT_ORIGINAL,
        "thumb": IMAGE_VARIANT_THUMBNAIL,
        "thumbnail": IMAGE_VARIANT_THUMBNAIL,
        "mini": IMAGE_VARIANT_PREVIEW,
        "preview": IMAGE_VARIANT_PREVIEW,
    }
    variant = aliases.get(normalized)
    if variant is None:
        return None, _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "variant", "issue": "must be one of: original, thumbnail, preview"}],
        )
    return variant, None


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
    return _normalize_known_image_tag(normalized), None


def _normalize_known_image_tag(value):
    normalized = str(value or "").strip()
    if not normalized:
        return normalized

    collapsed = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    if collapsed.startswith("reference"):
        return IMAGE_BROWSER_TAG_REFERENCE
    canonical_tags = {
        "box": IMAGE_BROWSER_TAG_BOX,
        "boxfront": IMAGE_BROWSER_TAG_BOX_FRONT,
        "boxside": IMAGE_BROWSER_TAG_BOX_SIDE,
        "boxback": IMAGE_BROWSER_TAG_BOX_BACK,
        "completed": IMAGE_BROWSER_TAG_COMPLETED,
        "complete": IMAGE_BROWSER_TAG_COMPLETED,
        "inprogress": IMAGE_BROWSER_TAG_IN_PROGRESS,
    }
    return canonical_tags.get(collapsed, normalized)


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
        "Return one JSON object only, with exactly these keys and types: "
        "title (string|null), series_name (string|null), series_number (string|null), manufacturer (string|null), "
        "artist (string|null), piece_count (integer|null), tags (string|array|null), dimensions_cm (string|null), "
        "description (string|null). "
        "All keys must always be present. "
        "Use null when unknown or not visible. "
        "Keep title and series fields separate. "
        "Prefer manufacturer key; publisher is acceptable only when manufacturer text is not available. "
        "Do not guess missing values. "
        "piece_count must be an integer when present. "
        "tags must be either a comma-separated string or an array of short strings. "
        "Do not include markdown, code fences, comments, or any text before/after the JSON object. "
        "Output must be parseable by json.loads without preprocessing."
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
            AiUsageEvent.status == AI_USAGE_STATUS_SUCCESS,
            AiUsageEvent.created_at >= day_start,
            AiUsageEvent.created_at < day_end,
        )
    ).scalar_one()
    return _to_decimal(spend) or Decimal("0")


def _record_ai_usage_event(
    *,
    db_session,
    operation,
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
        operation=operation,
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
            if item is None:
                continue
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                item = str(item)
            if not isinstance(item, str):
                continue
            tag, error = _validate_optional_text_field(item, field_name="tags", max_length=64)
            if error is not None:
                continue
            if tag:
                normalized_items.append(tag)

        joined = ", ".join(normalized_items)
        return _validate_optional_text_field(joined, field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)

    if isinstance(raw_tags, (int, float)) and not isinstance(raw_tags, bool):
        return _validate_optional_text_field(str(raw_tags), field_name="tags", max_length=JIGSAW_TAGS_MAX_LENGTH)

    return None, None


def _parse_optional_ai_piece_count(value):
    piece_count, error = _parse_optional_positive_integer(value, "piece_count")
    if error is None:
        return piece_count, None

    if not isinstance(value, str):
        return None, None

    digit_match = re.search(r"\d[\d,\.\s]*", value)
    if digit_match is None:
        return None, None

    numeric_text = re.sub(r"[^0-9]", "", digit_match.group(0))
    if not numeric_text:
        return None, None

    try:
        parsed = int(numeric_text)
    except ValueError:
        return None, None

    if parsed <= 0:
        return None, None
    return parsed, None


def _coerce_ai_optional_text_field(value, *, field_name, max_length):
    if value is None:
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        return None, None
    return _validate_optional_text_field(value, field_name=field_name, max_length=max_length)


def _normalize_ai_jigsaw_payload(raw_payload):
    if not isinstance(raw_payload, dict):
        return None, _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "ai_response", "issue": "must be a JSON object"}],
        )

    title, error = _coerce_ai_optional_text_field(raw_payload.get("title"), field_name="title", max_length=JIGSAW_TITLE_MAX_LENGTH)
    if error is not None:
        title = None

    series_name, error = _coerce_ai_optional_text_field(
        raw_payload.get("series_name"),
        field_name="series_name",
        max_length=JIGSAW_SERIES_NAME_MAX_LENGTH,
    )
    if error is not None:
        series_name = None

    series_number, error = _coerce_ai_optional_text_field(
        raw_payload.get("series_number"),
        field_name="series_number",
        max_length=JIGSAW_SERIES_NUMBER_MAX_LENGTH,
    )
    if error is not None:
        series_number = None

    manufacturer_source = raw_payload.get("manufacturer")
    if manufacturer_source is None:
        manufacturer_source = raw_payload.get("publisher")
    manufacturer, error = _coerce_ai_optional_text_field(
        manufacturer_source,
        field_name="manufacturer",
        max_length=JIGSAW_MANUFACTURER_MAX_LENGTH,
    )
    if error is not None:
        manufacturer = None

    artist, error = _coerce_ai_optional_text_field(raw_payload.get("artist"), field_name="artist", max_length=JIGSAW_ARTIST_MAX_LENGTH)
    if error is not None:
        artist = None

    dimensions_cm, error = _coerce_ai_optional_text_field(
        raw_payload.get("dimensions_cm"),
        field_name="dimensions_cm",
        max_length=JIGSAW_DIMENSIONS_MAX_LENGTH,
    )
    if error is not None:
        dimensions_cm = None

    description, error = _coerce_ai_optional_text_field(
        raw_payload.get("description"),
        field_name="description",
        max_length=JIGSAW_DESCRIPTION_MAX_LENGTH,
    )
    if error is not None:
        description = None

    piece_count, error = _parse_optional_ai_piece_count(raw_payload.get("piece_count"))
    if error is not None:
        piece_count = None

    tags, error = _normalize_ai_tags(raw_payload.get("tags"))
    if error is not None:
        tags = None

    return {
        "title": title,
        "series_name": series_name,
        "series_number": series_number,
        "manufacturer": manufacturer,
        "artist": artist,
        "dimensions_cm": dimensions_cm,
        "description": description,
        "piece_count": piece_count,
        "tags": tags,
    }, None


def _extract_ai_message_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                text_parts.append(text_value)
        return "\n".join(text_parts)

    return ""


def _infer_jigsaw_metadata_from_images(images, instruction_text):
    if not current_app.config.get("AI_ENABLED", False):
        raise RuntimeError("AI image inference is disabled")

    api_key = (current_app.config.get("AI_API_KEY") or "").strip()
    endpoint_url = (current_app.config.get("AI_ENDPOINT_URL") or "").strip()
    model = (current_app.config.get("AI_MODEL") or "").strip()
    timeout_seconds = int(current_app.config.get("AI_TIMEOUT_SECONDS") or 60)

    if not api_key or not endpoint_url or not model:
        raise RuntimeError("AI image inference configuration is incomplete")

    if not isinstance(images, list) or len(images) == 0:
        raise RuntimeError("No images were supplied for AI metadata inference")

    user_content = [{"type": "text", "text": instruction_text}]
    for image in images:
        image_base64 = base64.b64encode(image.image_data).decode("ascii")
        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime_type};base64,{image_base64}",
                },
            }
        )

    request_payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _build_ai_image_prompt()},
            {"role": "user", "content": user_content},
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
        provider_body = ""
        try:
            provider_body = error.read().decode("utf-8", errors="replace")
        except OSError:
            provider_body = ""

        compact_body = re.sub(r"\s+", " ", provider_body).strip()
        if compact_body:
            compact_preview = compact_body[:600]
            raise AiProviderRequestError(
                f"AI provider returned HTTP {error.code}: {compact_preview}",
                status_code=error.code,
                response_text=provider_body,
            ) from error
        raise AiProviderRequestError(
            f"AI provider returned HTTP {error.code}",
            status_code=error.code,
            response_text=provider_body or None,
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AiProviderRequestError(f"AI provider request failed: {error}") from error

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

    parsed_payload = _extract_json_object_from_text(_extract_ai_message_text(content))
    if parsed_payload is None:
        raise RuntimeError("AI provider did not return a valid metadata JSON object")

    cost_payload = _build_ai_usage_costs(result_payload)
    return {
        "metadata": parsed_payload,
        "provider_response": result_payload,
        "provider_response_text": response_raw,
        "prompt_tokens": cost_payload["prompt_tokens"],
        "completion_tokens": cost_payload["completion_tokens"],
        "total_tokens": cost_payload["total_tokens"],
        "provider_cost_usd": cost_payload["provider_cost_usd"],
        "computed_cost_usd": cost_payload["computed_cost_usd"],
        "final_cost_usd": cost_payload["final_cost_usd"],
        "model": model,
        "endpoint_url": endpoint_url,
    }


def _infer_jigsaw_metadata_from_image(image):
    return _infer_jigsaw_metadata_from_images([image], "Extract jigsaw metadata from this image.")


def _is_missing_jigsaw_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _is_box_metadata_tag(tag_value):
    normalized = str(tag_value or "").strip().lower()
    if not normalized:
        return False
    explicit_box_tags = {
        IMAGE_BROWSER_TAG_BOX.lower(),
        IMAGE_BROWSER_TAG_BOX_FRONT.lower(),
        IMAGE_BROWSER_TAG_BOX_BACK.lower(),
        IMAGE_BROWSER_TAG_BOX_SIDE.lower(),
    }
    if normalized in explicit_box_tags:
        return True
    if normalized.startswith("box"):
        return True
    normalized_with_spaces = normalized.replace("_", " ").replace("-", " ")
    return normalized_with_spaces.startswith("box ")


def _apply_ai_metadata_to_jigsaw(*, jigsaw, normalized_payload, overwrite_existing=False):
    applied_fields = []
    skipped_fields = []

    candidate_fields = (
        "title",
        "series_name",
        "series_number",
        "manufacturer",
        "artist",
        "piece_count",
        "tags",
        "dimensions_cm",
        "description",
    )

    for field_name in candidate_fields:
        candidate_value = normalized_payload.get(field_name)
        if candidate_value is None:
            skipped_fields.append({"field": field_name, "reason": "ai_null"})
            continue

        current_value = getattr(jigsaw, field_name)
        if not overwrite_existing and not _is_missing_jigsaw_value(current_value):
            skipped_fields.append({"field": field_name, "reason": "already_set"})
            continue

        if current_value == candidate_value:
            skipped_fields.append({"field": field_name, "reason": "unchanged"})
            continue

        setattr(jigsaw, field_name, candidate_value)
        applied_fields.append(field_name)

    return applied_fields, skipped_fields


@api_v1_bp.get("/health")
def health_check():
    image_embeddings_enabled = bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False))
    image_embeddings_payload = {
        "enabled": image_embeddings_enabled,
    }
    if image_embeddings_enabled:
        model_name, model_revision, model_key, model_local_path, local_files_only = _get_embedding_model_config()
        runtime_error = embedding_runtime_error()
        image_embeddings_payload.update(
            {
                "model_name": model_name,
                "model_revision": model_revision,
                "model_key": model_key,
                "local_model_path": model_local_path or None,
                "local_files_only": local_files_only,
                "runtime_ready": runtime_error is None,
                "runtime_error": runtime_error,
            }
        )

    payload = {
        "status": "ok",
        "environment": current_app.config["APP_ENV"],
        "version": current_app.config.get("APP_VERSION", "0.0.0-dev"),
        "build_sha": current_app.config.get("APP_BUILD_SHA", "local"),
        "build_time": current_app.config.get("APP_BUILD_TIME", ""),
        "image_embeddings": image_embeddings_payload,
    }
    return _success_response(payload)


@api_v1_bp.get("/auth/stfd/login-url")
def stfd_login_url():
    if not _is_stfd_enabled():
        return _success_response({"enabled": False, "allow_local_login": True, "login_url": None})

    stfd_config, config_error = _validate_stfd_runtime_config()
    if config_error is not None:
        return config_error

    return _success_response(
        {
            "enabled": True,
            "allow_local_login": bool(current_app.config.get("STFD_ALLOW_LOCAL_LOGIN", False)),
            "login_url": _build_stfd_login_url(stfd_config),
        }
    )


@api_v1_bp.post("/auth/login")
def auth_login():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    if _is_stfd_enabled():
        token = payload.get("token")
        if isinstance(token, str) and token.strip():
            return _auth_login_via_stfd_token(token.strip())

        allow_local_login = bool(current_app.config.get("STFD_ALLOW_LOCAL_LOGIN", False))
        if not allow_local_login:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [
                    {
                        "field": "token",
                        "issue": "must be a non-empty string when STFD authentication is enabled and local login fallback is disabled",
                    }
                ],
            )

    email, error = _validate_login_email(payload.get("email"))
    if error is not None:
        return error

    password, error = _validate_password(payload.get("password"))
    if error is not None:
        return error

    rate_limit_response = _check_login_rate_limit(email)
    if rate_limit_response is not None:
        payload, status_code, retry_after_seconds = rate_limit_response
        response = current_app.response_class(
            response=json.dumps(payload),
            status=status_code,
            mimetype="application/json",
        )
        response.headers["Retry-After"] = str(retry_after_seconds)
        return response

    db_session = get_session()
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not user.is_active or not user.check_password(password):
        _record_failed_login_attempt(email)
        return _error_response("authentication_failed", "Invalid credentials.", 401)

    _clear_failed_login_attempts(email)
    role_names = _get_role_names_for_user_id(user.id)
    csrf_token = token_urlsafe(24)

    session.clear()
    user_session = _create_user_session_record(db_session, user_id=user.id, auth_provider="local")
    session["user_id"] = user.id
    session["csrf_token"] = csrf_token
    session["auth_provider"] = "local"
    session[SESSION_IDENTIFIER_KEY] = user_session.session_identifier
    session.permanent = True
    g.current_user = user
    g.current_user_roles = role_names
    g.current_user_auth_provider = "local"

    _record_audit_event(
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        payload={"roles": sorted(role_names), "session_record_id": user_session.id},
    )
    db_session.commit()

    return _success_response(
        {
            "user": _serialize_user(user, role_names),
            "csrf_token": csrf_token,
            "auth_provider": "local",
            "session_identifier": user_session.session_identifier,
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
            "auth_provider": getattr(g, "current_user_auth_provider", "local"),
            "session_identifier": str(session.get(SESSION_IDENTIFIER_KEY) or "") or None,
        }
    )


@api_v1_bp.patch("/auth/me")
@require_auth
def update_auth_me():
    if _is_stfd_enabled():
        return _error_response(
            "forbidden",
            "Account profile and password changes are managed by STFD.",
            403,
        )

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
            "auth_provider": getattr(g, "current_user_auth_provider", "local"),
            "session_identifier": str(session.get(SESSION_IDENTIFIER_KEY) or "") or None,
        }
    )


@api_v1_bp.post("/auth/logout")
@require_auth
def auth_logout():
    db_session = get_session()
    session_identifier = str(session.get(SESSION_IDENTIFIER_KEY) or "").strip()
    if session_identifier:
        user_session = db_session.execute(
            select(UserSession).where(
                UserSession.user_id == g.current_user.id,
                UserSession.session_identifier == session_identifier,
            )
        ).scalar_one_or_none()
        _terminate_user_session_record(
            db_session,
            user_session,
            reason=SESSION_TERMINATION_REASON_LOGOUT,
            terminated_by_user_id=g.current_user.id,
        )

    _record_audit_event(
        action="auth.logout",
        entity_type="user",
        entity_id=g.current_user.id,
    )
    db_session.commit()

    session.clear()

    g.current_user = None
    g.current_user_roles = []
    return _success_response({"logged_out": True})


@api_v1_bp.get("/roles")
@require_role("administrator")
def list_roles():
    db_session = get_session()
    roles = db_session.execute(select(Role).order_by(Role.name)).scalars().all()
    payload = [{"id": role.id, "name": role.name, "uni": role.uni, "description": role.description} for role in roles]
    return _success_response(payload)


@api_v1_bp.get("/audit-events")
@require_auth
def list_audit_events():
    if not _current_user_has_capability("audit.read"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    pagination, error = _parse_list_pagination_query(default_page_size=25, max_page_size=200, legacy_limit_max=200)
    if error is not None:
        return error

    db_session = get_session()
    events_stmt = select(AuditEvent)
    if "administrator" not in g.current_user_roles:
        events_stmt = events_stmt.where(AuditEvent.actor_user_id == g.current_user.id)

    total_items = int(db_session.execute(select(func.count()).select_from(events_stmt.subquery())).scalar_one() or 0)
    events = db_session.execute(
        events_stmt
        .order_by(AuditEvent.id.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
    ).scalars().all()
    payload = [_serialize_audit_event(event) for event in events]
    return _success_list_response(
        payload,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_items=total_items,
    )


@api_v1_bp.get("/security/blocked-ips")
@require_role("administrator")
def list_blocked_ips():
    db_session = get_session()
    include_expired = str(request.args.get("include_expired") or "").strip().lower() in {"1", "true", "yes", "on"}
    now = datetime.now(timezone.utc)

    stmt = select(BlockedIp)
    if not include_expired:
        stmt = stmt.where(BlockedIp.blocked_until > now)

    blocked_ips = db_session.execute(stmt.order_by(BlockedIp.blocked_until.desc(), BlockedIp.id.desc())).scalars().all()
    return _success_response([_serialize_blocked_ip(entry) for entry in blocked_ips])


@api_v1_bp.post("/security/blocked-ips")
@require_role("administrator")
def create_or_extend_blocked_ip():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    normalized_ip = normalize_ip_address(payload.get("ip_address"))
    if not normalized_ip:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "ip_address", "issue": "must be a valid IPv4 or IPv6 address"}],
        )

    raw_duration_hours = payload.get("duration_hours", 24)
    if not isinstance(raw_duration_hours, int) or isinstance(raw_duration_hours, bool):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "duration_hours", "issue": "must be an integer between 1 and 720"}],
        )

    duration_hours = int(raw_duration_hours)
    if duration_hours < 1 or duration_hours > IP_BLOCK_MAX_DURATION_HOURS:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "duration_hours", "issue": "must be between 1 and 720"}],
        )

    reason, reason_error = _validate_optional_text_field(
        payload.get("reason"),
        field_name="reason",
        max_length=IP_BLOCK_REASON_MAX_LENGTH,
    )
    if reason_error is not None:
        return reason_error

    notes, notes_error = _validate_optional_text_field(
        payload.get("notes"),
        field_name="notes",
        max_length=IP_BLOCK_NOTES_MAX_LENGTH,
    )
    if notes_error is not None:
        return notes_error

    blocked_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
    db_session = get_session()
    try:
        blocked_ip = upsert_blocked_ip(
            db_session,
            ip_address=normalized_ip,
            blocked_until=blocked_until,
            block_source=MANUAL_BLOCK_SOURCE,
            block_reason=reason,
            notes=notes,
            created_by_user_id=g.current_user.id,
            add_hit=False,
            exempt_cidrs=current_app.config.get("TRUSTED_CLIENT_CIDRS", []),
        )
    except ValueError as error:
        return _error_response("conflict", str(error), 409)

    _record_audit_event(
        action="security.blocked_ip_upserted",
        entity_type="blocked_ip",
        entity_id=blocked_ip.id,
        payload={
            "ip_address": blocked_ip.ip_address,
            "duration_hours": duration_hours,
            "block_source": blocked_ip.block_source,
            "block_reason": blocked_ip.block_reason,
        },
    )
    db_session.commit()
    return _success_response(_serialize_blocked_ip(blocked_ip), status_code=201)


@api_v1_bp.delete("/security/blocked-ips/<int:blocked_ip_id>")
@require_role("administrator")
def delete_blocked_ip(blocked_ip_id):
    db_session = get_session()
    blocked_ip = db_session.get(BlockedIp, blocked_ip_id)
    if blocked_ip is None:
        return _error_response("not_found", "Blocked IP entry was not found.", 404)

    ip_address = blocked_ip.ip_address
    db_session.delete(blocked_ip)
    _record_audit_event(
        action="security.blocked_ip_removed",
        entity_type="blocked_ip",
        entity_id=blocked_ip_id,
        payload={"ip_address": ip_address},
    )
    db_session.commit()
    return _success_response({"removed": True, "id": blocked_ip_id, "ip_address": ip_address})


@api_v1_bp.get("/security/sessions")
@require_role("administrator")
def list_active_user_sessions():
    db_session = get_session()
    now = datetime.now(timezone.utc)
    cutoff = _get_session_inactivity_cutoff(now)

    sessions = db_session.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.terminated_at.is_(None),
            UserSession.last_activity_at > cutoff,
        )
        .order_by(UserSession.last_activity_at.desc(), UserSession.id.desc())
    ).all()
    payload = [_serialize_user_session(user_session, user) for user_session, user in sessions]
    return _success_response(payload)


@api_v1_bp.delete("/security/sessions/<int:user_session_id>")
@require_role("administrator")
def terminate_user_session(user_session_id):
    db_session = get_session()
    user_session = db_session.get(UserSession, user_session_id)
    if user_session is None:
        return _error_response("not_found", "Session entry was not found.", 404)

    if user_session.terminated_at is not None:
        return _error_response("conflict", "Session is already terminated.", 409)

    target_user = db_session.get(User, user_session.user_id)
    _terminate_user_session_record(
        db_session,
        user_session,
        reason=SESSION_TERMINATION_REASON_ADMIN_TERMINATED,
        terminated_by_user_id=g.current_user.id,
    )
    _record_audit_event(
        action="security.session_terminated",
        entity_type="user_session",
        entity_id=user_session.id,
        payload={
            "terminated_user_id": user_session.user_id,
            "terminated_user_email": getattr(target_user, "email", None),
            "origin_ip_address": user_session.origin_ip_address,
        },
    )
    db_session.commit()

    if str(session.get(SESSION_IDENTIFIER_KEY) or "").strip() == user_session.session_identifier:
        session.clear()
        g.current_user = None
        g.current_user_roles = []

    return _success_response({"terminated": True, "id": user_session.id})


@api_v1_bp.get("/system/database-backups")
@require_role("administrator")
def list_database_backups():
    db_session = get_session()
    backups = db_session.execute(select(DatabaseBackup).order_by(DatabaseBackup.id.desc())).scalars().all()
    return _success_response([_serialize_database_backup(entry) for entry in backups])


@api_v1_bp.post("/system/database-backups")
@require_role("administrator")
def create_database_backup():
    db_session = get_session()
    now = datetime.now(timezone.utc)
    backup_root = _resolve_database_backup_root_path()
    backup_root.mkdir(parents=True, exist_ok=True)

    app_env = str(current_app.config.get("APP_ENV", "dev") or "dev").strip() or "dev"
    app_version = str(current_app.config.get("APP_VERSION", "0.0.0") or "0.0.0").strip() or "0.0.0"
    compression = _resolve_database_backup_compression()
    filename = _build_unique_backup_filename(
        backup_root=backup_root,
        generated_at=now,
        app_env=app_env,
        app_version=app_version,
        compression=compression,
    )
    storage_path = (backup_root / filename).resolve()

    backup_record = DatabaseBackup(
        initiated_by_user_id=g.current_user.id,
        filename=filename,
        storage_path=str(storage_path),
        file_format=DATABASE_BACKUP_FORMAT_MYSQL_SQL,
        status=DATABASE_BACKUP_STATUS_QUEUED,
        app_environment=app_env,
        app_version=app_version,
        created_at=now,
    )
    db_session.add(backup_record)
    db_session.flush()

    _record_audit_event(
        action="system.database_backup_requested",
        entity_type="database_backup",
        entity_id=backup_record.id,
        payload={
            "filename": backup_record.filename,
            "app_environment": normalize_environment_label(app_env),
            "app_version": app_version,
        },
    )
    db_session.commit()

    _start_database_backup_job(backup_record.id)
    return _success_response(_serialize_database_backup(backup_record), status_code=202)


@api_v1_bp.get("/system/database-backups/<int:backup_id>/download")
@require_role("administrator")
def download_database_backup(backup_id):
    db_session = get_session()
    backup_record = db_session.get(DatabaseBackup, backup_id)
    if backup_record is None:
        return _error_response("not_found", "Database backup entry was not found.", 404)

    if str(backup_record.status or "").strip().lower() != DATABASE_BACKUP_STATUS_COMPLETED:
        return _error_response("conflict", "Database backup is not ready for download.", 409)

    try:
        backup_path = _resolve_database_backup_file_path(backup_record)
    except RuntimeError as error:
        return _error_response("conflict", str(error), 409)

    if not backup_path.exists() or not backup_path.is_file():
        return _error_response("not_found", "Backup file is missing from storage.", 404)

    backup_content = backup_path.read_bytes()
    _record_audit_event(
        action="system.database_backup_downloaded",
        entity_type="database_backup",
        entity_id=backup_record.id,
        payload={
            "filename": backup_record.filename,
            "file_size_bytes": len(backup_content),
        },
    )
    db_session.commit()

    response = current_app.response_class(backup_content, mimetype=_resolve_database_backup_mime_type(backup_record.filename))
    response.headers["Content-Disposition"] = f'attachment; filename="{backup_record.filename}"'
    response.headers["Content-Length"] = str(len(backup_content))
    response.headers["Cache-Control"] = "no-store"
    return response


@api_v1_bp.delete("/system/database-backups/<int:backup_id>")
@require_role("administrator")
def delete_database_backup(backup_id):
    db_session = get_session()
    backup_record = db_session.get(DatabaseBackup, backup_id)
    if backup_record is None:
        return _error_response("not_found", "Database backup entry was not found.", 404)

    status = str(backup_record.status or "").strip().lower()
    if status in {DATABASE_BACKUP_STATUS_QUEUED, DATABASE_BACKUP_STATUS_RUNNING}:
        return _error_response("conflict", "Database backup is still running and cannot be deleted yet.", 409)

    backup_path = None
    path_error = None
    try:
        backup_path = _resolve_database_backup_file_path(backup_record)
    except RuntimeError as error:
        path_error = str(error)

    if backup_path is not None:
        temp_path = backup_path.with_suffix(backup_path.suffix + ".tmp")
        if temp_path.exists() and temp_path.is_file():
            temp_path.unlink()
        if backup_path.exists() and backup_path.is_file():
            backup_path.unlink()

    deleted_filename = str(backup_record.filename or "")
    deleted_id = int(backup_record.id)
    db_session.delete(backup_record)
    _record_audit_event(
        action="system.database_backup_deleted",
        entity_type="database_backup",
        entity_id=deleted_id,
        payload={
            "filename": deleted_filename,
            "path_warning": path_error,
        },
    )
    db_session.commit()
    return _success_response({"deleted": True, "id": deleted_id, "filename": deleted_filename})


@api_v1_bp.get("/ai-usage/diagnostics")
@require_role("administrator")
def get_ai_usage_diagnostics():
    pagination, error = _parse_list_pagination_query(default_page_size=25, max_page_size=200, legacy_limit_max=200)
    if error is not None:
        return error

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    seven_days_start = now - timedelta(days=7)
    thirty_days_start = now - timedelta(days=30)

    db_session = get_session()

    windows = {
        "today": _build_ai_usage_window_summary(db_session, start_at=today_start, end_at=now),
        "last_7_days": _build_ai_usage_window_summary(db_session, start_at=seven_days_start, end_at=now),
        "last_30_days": _build_ai_usage_window_summary(db_session, start_at=thirty_days_start, end_at=now),
    }

    by_operation = _summarize_ai_usage_by_field(
        db_session,
        field_name="operation",
        start_at=thirty_days_start,
        end_at=now,
    )
    by_model = _summarize_ai_usage_by_field(
        db_session,
        field_name="model",
        start_at=thirty_days_start,
        end_at=now,
    )

    total_recent_calls = int(db_session.execute(select(func.count(AiUsageEvent.id))).scalar_one() or 0)
    recent_rows = db_session.execute(
        select(
            AiUsageEvent,
            JigsawImage.filename,
            JigsawImage.mime_type,
            func.length(JigsawImage.image_data).label("image_size_bytes"),
        )
        .outerjoin(JigsawImage, JigsawImage.id == AiUsageEvent.image_id)
        .order_by(AiUsageEvent.id.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
    ).all()
    recent_calls = [
        _serialize_ai_usage_event(
            event=row[0],
            image_filename=row[1],
            image_mime_type=row[2],
            image_size_bytes=int(row[3]) if row[3] is not None else None,
        )
        for row in recent_rows
    ]

    budget_usd = _to_decimal(current_app.config.get("AI_DAILY_BUDGET_USD"))
    daily_spend_usd = _get_daily_ai_spend(db_session)
    payload = {
        "windows": windows,
        "by_operation_30d": by_operation,
        "by_model_30d": by_model,
        "recent_calls": recent_calls,
        "recent_calls_pagination": {
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": total_recent_calls,
            "total_pages": max(1, (total_recent_calls + pagination["page_size"] - 1) // pagination["page_size"]),
        },
        "daily_budget_usd": str(budget_usd) if budget_usd is not None else None,
        "daily_spend_usd": str(daily_spend_usd),
        "daily_budget_reached": bool(
            budget_usd is not None and budget_usd >= Decimal("0") and daily_spend_usd >= budget_usd
        ),
    }
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


@api_v1_bp.delete("/users/<int:user_id>")
@require_role("administrator")
def delete_user(user_id):
    db_session = get_session()
    user = db_session.get(User, user_id)
    if user is None:
        return _error_response("not_found", "User was not found.", 404)

    if user.is_active:
        return _error_response("conflict", "Active users must be deactivated before deletion.", 409)

    now = datetime.now(timezone.utc)
    cutoff = _get_session_inactivity_cutoff(now)
    active_session_count = int(
        db_session.execute(
            select(func.count())
            .select_from(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.terminated_at.is_(None),
                UserSession.last_activity_at > cutoff,
            )
        ).scalar_one()
        or 0
    )
    if active_session_count > 0:
        return _error_response("conflict", "Cannot delete a user with an active session.", 409)

    deleted_role_count = int(
        db_session.execute(sa_delete(UserRole).where(UserRole.user_id == user.id)).rowcount or 0
    )
    deleted_session_count = int(
        db_session.execute(sa_delete(UserSession).where(UserSession.user_id == user.id)).rowcount or 0
    )
    deleted_loan_count = int(db_session.execute(sa_delete(Loan).where(Loan.borrower_user_id == user.id)).rowcount or 0)

    nullified_diary_updated_count = int(
        db_session.execute(
            sa_update(JigsawDiaryEntry)
            .where(JigsawDiaryEntry.updated_by_user_id == user.id)
            .values(updated_by_user_id=None)
        ).rowcount
        or 0
    )
    deleted_diary_entry_count = int(
        db_session.execute(sa_delete(JigsawDiaryEntry).where(JigsawDiaryEntry.created_by_user_id == user.id)).rowcount or 0
    )
    nullified_uploaded_image_count = int(
        db_session.execute(
            sa_update(JigsawImage).where(JigsawImage.uploaded_by_user_id == user.id).values(uploaded_by_user_id=None)
        ).rowcount
        or 0
    )

    deleted_audit_event_count = int(
        db_session.execute(
            sa_delete(AuditEvent).where(
                or_(
                    AuditEvent.actor_user_id == user.id,
                    (AuditEvent.entity_type == "user") & (AuditEvent.entity_id == str(user.id)),
                )
            )
        ).rowcount
        or 0
    )
    deleted_ai_usage_event_count = int(
        db_session.execute(sa_delete(AiUsageEvent).where(AiUsageEvent.actor_user_id == user.id)).rowcount or 0
    )

    bulk_job_ids = db_session.execute(
        select(BulkAiCreateJob.id).where(BulkAiCreateJob.actor_user_id == user.id)
    ).scalars().all()
    deleted_bulk_job_item_count = 0
    if bulk_job_ids:
        deleted_bulk_job_item_count = int(
            db_session.execute(sa_delete(BulkAiCreateJobItem).where(BulkAiCreateJobItem.job_id.in_(bulk_job_ids))).rowcount or 0
        )
    deleted_bulk_job_count = int(
        db_session.execute(sa_delete(BulkAiCreateJob).where(BulkAiCreateJob.actor_user_id == user.id)).rowcount or 0
    )

    nullified_embedding_job_count = int(
        db_session.execute(
            sa_update(ImageEmbeddingJob)
            .where(ImageEmbeddingJob.actor_user_id == user.id)
            .values(actor_user_id=None)
        ).rowcount
        or 0
    )
    nullified_blocked_ip_count = int(
        db_session.execute(sa_update(BlockedIp).where(BlockedIp.created_by_user_id == user.id).values(created_by_user_id=None)).rowcount
        or 0
    )

    deleted_user_id = int(user.id)
    deleted_user_email = user.email
    db_session.delete(user)

    _record_audit_event(
        action="user.deleted",
        entity_type="user",
        entity_id=deleted_user_id,
        payload={
            "email": deleted_user_email,
            "deleted_role_count": deleted_role_count,
            "deleted_session_count": deleted_session_count,
            "deleted_loan_count": deleted_loan_count,
            "deleted_diary_entry_count": deleted_diary_entry_count,
            "nullified_diary_updated_count": nullified_diary_updated_count,
            "nullified_uploaded_image_count": nullified_uploaded_image_count,
            "deleted_audit_event_count": deleted_audit_event_count,
            "deleted_ai_usage_event_count": deleted_ai_usage_event_count,
            "deleted_bulk_job_count": deleted_bulk_job_count,
            "deleted_bulk_job_item_count": deleted_bulk_job_item_count,
            "nullified_embedding_job_count": nullified_embedding_job_count,
            "nullified_blocked_ip_count": nullified_blocked_ip_count,
        },
    )
    db_session.commit()

    return _success_response({"id": deleted_user_id, "deleted": True})


@api_v1_bp.get("/jigsaws")
def list_jigsaws():
    _load_current_user()
    db_session = get_session()
    stmt = select(Jigsaw)

    if "administrator" not in getattr(g, "current_user_roles", []):
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

    use_pagination = any(param in request.args for param in ("page", "page_size", "limit"))
    if not use_pagination:
        jigsaws = db_session.execute(stmt.order_by(Jigsaw.id)).scalars().all()
        payload = [_serialize_jigsaw(jigsaw) for jigsaw in jigsaws]
        return _success_response(payload)

    pagination, error = _parse_list_pagination_query(default_page_size=25, max_page_size=200, legacy_limit_max=500)
    if error is not None:
        return error

    total_items = int(db_session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    jigsaws = db_session.execute(
        stmt.order_by(Jigsaw.id).offset(pagination["offset"]).limit(pagination["page_size"])
    ).scalars().all()
    payload = [_serialize_jigsaw(jigsaw) for jigsaw in jigsaws]
    return _success_list_response(
        payload,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_items=total_items,
    )


@api_v1_bp.get("/jigsaws/thumbnail-images")
def list_jigsaw_thumbnail_images():
    _load_current_user()
    db_session = get_session()

    stmt = select(*_jigsaw_image_metadata_columns()).where(JigsawImage.jigsaw_id.is_not(None))
    if "administrator" not in getattr(g, "current_user_roles", []):
        stmt = stmt.join(Jigsaw, Jigsaw.id == JigsawImage.jigsaw_id).where(Jigsaw.status != JigsawStatus.RETIRED)

    image_rows = db_session.execute(stmt.order_by(JigsawImage.id.desc())).all()

    preferred_by_jigsaw_id = {}
    for image_row in image_rows:
        image = _serialize_jigsaw_image_fields(
            image_id=image_row.id,
            jigsaw_id=image_row.jigsaw_id,
            uploaded_by_user_id=image_row.uploaded_by_user_id,
            tag=image_row.tag,
            filename=image_row.filename,
            mime_type=image_row.mime_type,
            content_version=image_row.content_version,
            captured_at=image_row.captured_at,
            captured_at_source=image_row.captured_at_source,
            user_comment=image_row.user_comment,
            created_at=image_row.created_at,
        )
        jigsaw_id = int(image.get("jigsaw_id") or 0)
        if jigsaw_id <= 0:
            continue

        existing = preferred_by_jigsaw_id.get(jigsaw_id)
        if existing is None:
            preferred_by_jigsaw_id[jigsaw_id] = image
            continue

        candidate_priority = _jigsaw_thumbnail_tag_priority(image.get("tag"))
        existing_priority = _jigsaw_thumbnail_tag_priority(existing.get("tag"))
        if candidate_priority < existing_priority:
            preferred_by_jigsaw_id[jigsaw_id] = image

    payload = list(preferred_by_jigsaw_id.values())
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
    if "member" not in borrower_roles and "borrower" not in borrower_roles and "administrator" not in borrower_roles:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "borrower_user_id", "issue": "must reference a member, borrower, or administrator user"}],
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


@api_v1_bp.post("/loans/<int:loan_id>/return")
@require_role("administrator")
def return_loan(loan_id):
    db_session = get_session()
    loan = db_session.get(Loan, loan_id)
    if loan is None:
        return _error_response("not_found", "Loan was not found.", 404)

    if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
        return _error_response("conflict", "Loan is not active and cannot be returned.", 409)

    returned_at = datetime.now(timezone.utc)
    loan.returned_at = returned_at
    loan.status = LoanStatus.RETURNED

    jigsaw = db_session.get(Jigsaw, loan.jigsaw_id)
    if jigsaw is not None and jigsaw.status == JigsawStatus.ON_LOAN:
        jigsaw.status = JigsawStatus.AVAILABLE

    _record_audit_event(
        action="loan.returned",
        entity_type="loan",
        entity_id=loan.id,
        payload={
            "borrower_user_id": loan.borrower_user_id,
            "jigsaw_id": loan.jigsaw_id,
            "returned_at": returned_at.isoformat(),
        },
    )
    db_session.commit()

    return _success_response(_serialize_loan(loan))


@api_v1_bp.post("/jigsaws")
@require_auth
def create_jigsaw():
    if not _current_user_has_capability("jigsaw.create"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    title, error = _validate_optional_text_field(payload.get("title"), field_name="title", max_length=JIGSAW_TITLE_MAX_LENGTH)
    if error is not None:
        return error

    series_name, error = _validate_optional_text_field(
        payload.get("series_name"),
        field_name="series_name",
        max_length=JIGSAW_SERIES_NAME_MAX_LENGTH,
    )
    if error is not None:
        return error

    series_number, error = _validate_optional_text_field(
        payload.get("series_number"),
        field_name="series_number",
        max_length=JIGSAW_SERIES_NUMBER_MAX_LENGTH,
    )
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
        series_name=series_name,
        series_number=series_number,
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
            "series_name": jigsaw.series_name,
            "series_number": jigsaw.series_number,
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
@require_auth
def update_jigsaw(jigsaw_id):
    if not _current_user_has_capability("jigsaw.update"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    updatable_fields = {
        "title",
        "series_name",
        "series_number",
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

    if "series_name" in payload:
        series_name, error = _validate_optional_text_field(
            payload.get("series_name"),
            field_name="series_name",
            max_length=JIGSAW_SERIES_NAME_MAX_LENGTH,
        )
        if error is not None:
            return error
        jigsaw.series_name = series_name

    if "series_number" in payload:
        series_number, error = _validate_optional_text_field(
            payload.get("series_number"),
            field_name="series_number",
            max_length=JIGSAW_SERIES_NUMBER_MAX_LENGTH,
        )
        if error is not None:
            return error
        jigsaw.series_number = series_number

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
        if "administrator" not in g.current_user_roles and status == JigsawStatus.RETIRED:
            return _error_response(
                "forbidden",
                "You do not have permission to access this resource.",
                403,
            )
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
@require_auth
def list_jigsaw_images(jigsaw_id):
    if not _current_user_has_capability("image.manage_library"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)
    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    image_rows = db_session.execute(
        select(*_jigsaw_image_metadata_columns())
        .where(JigsawImage.jigsaw_id == jigsaw.id)
        .order_by(JigsawImage.id.desc())
    ).all()
    payload = [
        _serialize_jigsaw_image_fields(
            image_id=row.id,
            jigsaw_id=row.jigsaw_id,
            uploaded_by_user_id=row.uploaded_by_user_id,
            tag=row.tag,
            filename=row.filename,
            mime_type=row.mime_type,
            content_version=row.content_version,
            captured_at=row.captured_at,
            captured_at_source=row.captured_at_source,
            user_comment=row.user_comment,
            created_at=row.created_at,
        )
        for row in image_rows
    ]
    return _success_response(payload)


@api_v1_bp.post("/jigsaws/<int:jigsaw_id>/images")
@require_auth
def create_jigsaw_image(jigsaw_id):
    if not _current_user_has_capability("image.upload"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)
    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    tag, error = _validate_optional_text_field(
        request.form.get("tag"), field_name="tag", max_length=JIGSAW_IMAGE_TAG_MAX_LENGTH
    )
    if error is not None:
        return error
    if tag is None:
        tag = DEFAULT_JIGSAW_IMAGE_TAG
    else:
        tag = _normalize_known_image_tag(tag)

    user_comment, error = _validate_optional_text_field(
        request.form.get("comment"), field_name="comment", max_length=JIGSAW_IMAGE_COMMENT_MAX_LENGTH
    )
    if error is not None:
        return error

    defer_processing = _is_truthy_form_value(request.form.get("defer_processing"))

    upload = request.files.get("image")
    if upload is None:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "file is required"}],
        )

    mime_type = (upload.mimetype or "").strip().lower()
    if not _is_allowed_image_mime_type(mime_type):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "must be a supported raster image type"}],
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

    captured_at = None
    captured_at_source = None
    captured_at_raw = None
    if not defer_processing:
        captured_at, captured_at_source, captured_at_raw = _extract_image_captured_at(image_data)

    image_sha256 = _compute_image_sha256(image_data)
    duplicate_image = db_session.execute(
        select(JigsawImage).where(JigsawImage.image_sha256 == image_sha256).order_by(JigsawImage.id.asc())
    ).scalar_one_or_none()
    if duplicate_image is not None:
        metadata_backfilled = _backfill_image_capture_metadata(
            duplicate_image,
            captured_at,
            captured_at_source,
            captured_at_raw,
        )
        comment_backfilled = _backfill_image_user_comment(duplicate_image, user_comment)
        uploaded_by_backfilled = _backfill_image_uploaded_by(duplicate_image, getattr(g.current_user, "id", None))
        _record_audit_event(
            action="jigsaw.image_duplicate_ignored",
            entity_type="jigsaw_image",
            entity_id=duplicate_image.id,
            payload={
                "jigsaw_id": jigsaw.id,
                "source_filename": filename,
                "duplicate_hash": image_sha256,
                "metadata_backfilled": metadata_backfilled,
                "comment_backfilled": comment_backfilled,
                "uploaded_by_backfilled": uploaded_by_backfilled,
            },
        )
        db_session.commit()
        return _success_response(_serialize_jigsaw_image(duplicate_image))

    try:
        variants = None
        if defer_processing:
            variants = {
                "thumbnail_mime_type": None,
                "thumbnail_data": None,
                "preview_mime_type": None,
                "preview_data": None,
            }

        image = _create_jigsaw_image_record(
            db_session,
            jigsaw_id=jigsaw.id,
            tag=tag,
            filename=filename,
            mime_type=mime_type,
            image_data=image_data,
            image_sha256=image_sha256,
            captured_at=captured_at,
            captured_at_source=captured_at_source,
            captured_at_raw=captured_at_raw,
            user_comment=user_comment,
            uploaded_by_user_id=getattr(g.current_user, "id", None),
            variants=variants,
        )

        _maybe_create_diary_entry_from_image(
            db_session=db_session,
            jigsaw=jigsaw,
            image=image,
            trigger="upload",
            created_by_user_id=g.current_user.id,
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
        if defer_processing:
            _queue_image_derivatives_refresh(image.id)
        _queue_image_embedding_refresh(image.id)
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
@require_auth
def list_image_library_images():
    if not _current_user_has_capability("image.manage_library"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    pagination, error = _parse_list_pagination_query(default_page_size=25, max_page_size=500, legacy_limit_max=500)
    if error is not None:
        return error

    db_session = get_session()
    total_items = int(db_session.execute(select(func.count(JigsawImage.id))).scalar_one() or 0)
    image_rows = db_session.execute(
        select(*_jigsaw_image_metadata_columns())
        .order_by(JigsawImage.id.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
    ).all()
    payload = [
        _serialize_jigsaw_image_fields(
            image_id=row.id,
            jigsaw_id=row.jigsaw_id,
            uploaded_by_user_id=row.uploaded_by_user_id,
            tag=row.tag,
            filename=row.filename,
            mime_type=row.mime_type,
            content_version=row.content_version,
            captured_at=row.captured_at,
            captured_at_source=row.captured_at_source,
            user_comment=row.user_comment,
            created_at=row.created_at,
        )
        for row in image_rows
    ]
    return _success_list_response(
        payload,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_items=total_items,
    )


@api_v1_bp.post("/image-embeddings/backfill")
@require_role("administrator")
def create_image_embedding_backfill_job():
    if not bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False)):
        return _error_response("conflict", "Image embeddings are disabled in server configuration.", 409)

    runtime_error = embedding_runtime_error()
    if runtime_error is not None and not _allow_image_embeddings_test_fallback():
        return _error_response(
            "conflict",
            "Image embeddings runtime dependencies are unavailable.",
            409,
            [{"field": "image_embeddings", "issue": runtime_error}],
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    requested_scope = str(payload.get("scope") or IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL).strip().lower()
    if requested_scope not in {IMAGE_EMBEDDING_BACKFILL_SCOPE_ALL, IMAGE_EMBEDDING_BACKFILL_SCOPE_MISSING}:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "scope", "issue": "must be one of: all, missing"}],
        )

    db_session = get_session()
    job = _create_image_embedding_backfill_job(db_session, scope=requested_scope)
    return _success_response({"job": _serialize_image_embedding_job(job)}, status_code=202)


@api_v1_bp.get("/image-embeddings/backfill/<int:job_id>")
@require_role("administrator")
def get_image_embedding_backfill_job(job_id):
    db_session = get_session()
    job = db_session.get(ImageEmbeddingJob, job_id)
    if job is None:
        return _error_response("not_found", "Image embedding backfill job was not found.", 404)

    if (
        job.status == IMAGE_EMBEDDING_JOB_STATUS_QUEUED
        and not bool(current_app.config.get("IMAGE_EMBEDDINGS_INLINE", False))
    ):
        _queue_image_embedding_job(job.id)
        db_session.expire_all()
        job = db_session.get(ImageEmbeddingJob, job_id)

    return _success_response({"job": _serialize_image_embedding_job(job)})


@api_v1_bp.get("/image-embeddings/diagnostics")
@require_role("administrator")
def get_image_embedding_diagnostics():
    raw_missing_limit = request.args.get("missing_limit", "24")
    try:
        missing_limit = int(raw_missing_limit)
    except ValueError:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "missing_limit", "issue": "must be an integer"}],
        )
    if missing_limit < 1 or missing_limit > 200:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "missing_limit", "issue": "must be between 1 and 200"}],
        )

    db_session = get_session()
    payload = _build_image_embedding_diagnostics_payload(db_session, missing_preview_limit=missing_limit)
    return _success_response(payload)


@api_v1_bp.get("/image-library/images/<int:image_id>/match-suggestions")
@require_auth
def get_image_match_suggestions(image_id):
    if not _current_user_has_capability("image.assign"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    if not bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False)):
        return _error_response("conflict", "Image embeddings are disabled in server configuration.", 409)

    runtime_error = embedding_runtime_error()
    if runtime_error is not None and not _allow_image_embeddings_test_fallback():
        return _error_response(
            "conflict",
            "Image embeddings runtime dependencies are unavailable.",
            409,
            [{"field": "image_embeddings", "issue": runtime_error}],
        )

    raw_limit = request.args.get("limit", "3")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "limit", "issue": "must be an integer"}],
        )
    if limit < 1 or limit > 10:
        return _error_response(
            "validation_error",
            "Invalid request query.",
            422,
            [{"field": "limit", "issue": "must be between 1 and 10"}],
        )

    db_session = get_session()
    image_row = db_session.execute(
        select(JigsawImage.id, JigsawImage.tag, JigsawImage.jigsaw_id).where(JigsawImage.id == int(image_id)).limit(1)
    ).first()
    if image_row is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)
    resolved_image_id, image_tag, image_jigsaw_id = image_row

    if not _is_completed_image_tag(image_tag):
        return _error_response("conflict", "Image must be tagged as Completed before matching.", 409)
    if image_jigsaw_id is not None:
        return _error_response("conflict", "Image is already assigned to a jigsaw.", 409)

    model_name, model_revision, model_key, model_local_path, local_files_only = _get_embedding_model_config()
    allow_test_fallback = _allow_image_embeddings_test_fallback()

    query_embedding = db_session.execute(
        select(ImageEmbedding)
        .where(ImageEmbedding.image_id == int(resolved_image_id), ImageEmbedding.model_key == model_key)
        .limit(1)
    ).scalar_one_or_none()
    if query_embedding is None:
        try:
            image = db_session.get(JigsawImage, int(resolved_image_id))
            if image is None:
                return _error_response("not_found", "Jigsaw image was not found.", 404)
            query_embedding = _upsert_image_embedding_for_image(
                db_session,
                image,
                model_name=model_name,
                model_revision=model_revision,
                model_key=model_key,
                model_local_path=model_local_path,
                local_files_only=local_files_only,
                allow_test_fallback=allow_test_fallback,
            )
            db_session.commit()
        except Exception as error:
            db_session.rollback()
            return _error_response("conflict", f"Could not compute query image embedding: {error}", 409)

    query_vector = _parse_embedding_vector(query_embedding.vector_json if query_embedding else None)
    if not query_vector:
        return _error_response("conflict", "Query image embedding is unavailable.", 409)

    reference_tag_filter = _build_reference_tag_sql_filter(JigsawImage.tag)
    candidate_stmt = (
        select(
            ImageEmbedding.vector_json,
            JigsawImage.id,
            JigsawImage.jigsaw_id,
            JigsawImage.tag,
            Jigsaw.title,
        )
        .join(JigsawImage, JigsawImage.id == ImageEmbedding.image_id)
        .join(Jigsaw, Jigsaw.id == JigsawImage.jigsaw_id)
        .where(
            ImageEmbedding.model_key == model_key,
            JigsawImage.jigsaw_id.is_not(None),
        )
        .order_by(JigsawImage.id.asc())
    )
    if reference_tag_filter is not None:
        candidate_stmt = candidate_stmt.where(reference_tag_filter)

    candidates = db_session.execute(candidate_stmt).all()

    best_by_jigsaw_id = {}
    for candidate_vector_json, candidate_image_id, candidate_jigsaw_id, candidate_tag, candidate_jigsaw_title in candidates:
        if candidate_jigsaw_id is None:
            continue
        if not _is_reference_image_tag(candidate_tag):
            continue
        candidate_vector = _parse_embedding_vector(candidate_vector_json)
        if not candidate_vector:
            continue

        score = cosine_similarity(query_vector, candidate_vector)
        jigsaw_id = int(candidate_jigsaw_id)
        previous = best_by_jigsaw_id.get(jigsaw_id)
        if previous is None or score > previous["score"]:
            best_by_jigsaw_id[jigsaw_id] = {
                "jigsaw_id": jigsaw_id,
                "jigsaw_title": candidate_jigsaw_title,
                "score": float(score),
                "reference_image_id": int(candidate_image_id),
                "reference_tag": candidate_tag,
            }

    ranked = sorted(best_by_jigsaw_id.values(), key=lambda row: row["score"], reverse=True)[:limit]
    for item in ranked:
        score = item["score"]
        if score >= 0.82:
            confidence = "high"
        elif score >= 0.72:
            confidence = "medium"
        else:
            confidence = "low"
        item["confidence"] = confidence
        reference_image_id = int(item.get("reference_image_id") or 0)
        if reference_image_id > 0:
            item["reference_image"] = {
                "id": reference_image_id,
                "tag": item.get("reference_tag"),
                "content_url": f"/api/v1/images/{reference_image_id}/content",
                "thumbnail_url": f"/api/v1/images/{reference_image_id}/content?variant={IMAGE_VARIANT_THUMBNAIL}",
                "preview_url": f"/api/v1/images/{reference_image_id}/content?variant={IMAGE_VARIANT_PREVIEW}",
            }

    return _success_response(
        {
            "image_id": int(resolved_image_id),
            "model_key": model_key,
            "candidate_count": len(ranked),
            "candidates": ranked,
        }
    )


@api_v1_bp.post("/image-library/bulk-create-jigsaws")
@require_role("administrator")
def start_bulk_create_jigsaws_job():
    payload, error = _parse_json_object()
    if error is not None:
        return error

    raw_image_ids = payload.get("image_ids")
    if not isinstance(raw_image_ids, list) or len(raw_image_ids) == 0:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image_ids", "issue": "must be a non-empty list of positive integers"}],
        )

    image_ids = []
    seen_ids = set()
    for raw_id in raw_image_ids:
        if not isinstance(raw_id, int) or isinstance(raw_id, bool) or raw_id <= 0:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "image_ids", "issue": "must contain positive integers only"}],
            )
        if raw_id in seen_ids:
            continue
        seen_ids.add(raw_id)
        image_ids.append(raw_id)

    if len(image_ids) > 500:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image_ids", "issue": "must contain no more than 500 image ids"}],
        )

    db_session = get_session()
    refreshed_job = _create_bulk_ai_create_job(db_session, image_ids)
    return _success_response({"job": _serialize_bulk_ai_create_job(refreshed_job)}, status_code=202)


@api_v1_bp.post("/image-library/bulk-create-jigsaws/unassigned-box")
@require_role("administrator")
def start_bulk_create_jigsaws_for_unassigned_box_images():
    db_session = get_session()
    image_ids = db_session.execute(
        select(JigsawImage.id)
        .where(
            JigsawImage.jigsaw_id.is_(None),
            func.lower(func.coalesce(JigsawImage.tag, "")) == "box",
        )
        .order_by(JigsawImage.id.asc())
    ).scalars().all()

    if not image_ids:
        return _error_response(
            "conflict",
            "No unassigned box images were found to process.",
            409,
        )

    refreshed_job = _create_bulk_ai_create_job(db_session, [int(image_id) for image_id in image_ids])
    return _success_response({"job": _serialize_bulk_ai_create_job(refreshed_job)}, status_code=202)


@api_v1_bp.get("/image-library/bulk-create-jigsaws/<int:job_id>")
@require_role("administrator")
def get_bulk_create_jigsaws_job(job_id):
    db_session = get_session()
    job = db_session.get(BulkAiCreateJob, job_id)
    if job is None:
        return _error_response("not_found", "Bulk create job was not found.", 404)

    if (
        job.status == BULK_AI_CREATE_STATUS_QUEUED
        and not bool(current_app.config.get("BULK_AI_CREATE_INLINE", False))
    ):
        _queue_bulk_ai_create_job(job.id)
        db_session.expire_all()
        job = db_session.get(BulkAiCreateJob, job_id)

    return _success_response({"job": _serialize_bulk_ai_create_job(job)})


@api_v1_bp.get("/image-library/bulk-create-jigsaws/<int:job_id>/items")
@require_role("administrator")
def list_bulk_create_jigsaws_job_items(job_id):
    db_session = get_session()
    job = db_session.get(BulkAiCreateJob, job_id)
    if job is None:
        return _error_response("not_found", "Bulk create job was not found.", 404)

    pagination, error = _parse_list_pagination_query(default_page_size=25, max_page_size=500, legacy_limit_max=500)
    if error is not None:
        return error

    total_items = int(
        db_session.execute(
            select(func.count(BulkAiCreateJobItem.id)).where(BulkAiCreateJobItem.job_id == job.id)
        ).scalar_one()
        or 0
    )
    job_items = db_session.execute(
        select(BulkAiCreateJobItem)
        .where(BulkAiCreateJobItem.job_id == job.id)
        .order_by(BulkAiCreateJobItem.id.asc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
    ).scalars().all()

    payload = [_serialize_bulk_ai_create_job_item(job_item) for job_item in job_items]
    return _success_list_response(
        payload,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_items=total_items,
    )


@api_v1_bp.post("/image-library/uploads")
@require_auth
def upload_image_library_items():
    if not _current_user_has_capability("image.upload"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    db_session = get_session()

    jigsaw_id, associated_jigsaw, error = _resolve_optional_jigsaw_reference(db_session, request.form.get("jigsaw_id"))
    if error is not None:
        return error

    tag, error = _validate_optional_text_field(
        request.form.get("tag"), field_name="tag", max_length=JIGSAW_IMAGE_TAG_MAX_LENGTH
    )
    if error is not None:
        return error
    if tag is None:
        tag = DEFAULT_JIGSAW_IMAGE_TAG
    else:
        tag = _normalize_known_image_tag(tag)

    user_comment, error = _validate_optional_text_field(
        request.form.get("comment"), field_name="comment", max_length=JIGSAW_IMAGE_COMMENT_MAX_LENGTH
    )
    if error is not None:
        return error

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
    existing_jigsaw_titles_by_id = {}
    if image_hashes:
        existing_images = db_session.execute(
            select(JigsawImage).where(JigsawImage.image_sha256.in_(image_hashes)).order_by(JigsawImage.id.asc())
        ).scalars().all()
        for existing in existing_images:
            if existing.image_sha256 and existing.image_sha256 not in existing_images_by_hash:
                existing_images_by_hash[existing.image_sha256] = existing

        existing_jigsaw_ids = sorted(
            {
                existing.jigsaw_id
                for existing in existing_images
                if existing.jigsaw_id is not None
            }
        )
        if existing_jigsaw_ids:
            existing_jigsaw_titles_by_id = {
                jigsaw_id: (title.strip() if isinstance(title, str) and title.strip() else None)
                for jigsaw_id, title in db_session.execute(
                    select(Jigsaw.id, Jigsaw.title).where(Jigsaw.id.in_(existing_jigsaw_ids))
                ).all()
            }

    try:
        for item in image_items:
            image_sha256 = item.get("image_sha256")
            if image_sha256 and image_sha256 in existing_images_by_hash:
                existing_image = existing_images_by_hash[image_sha256]
                existing_jigsaw_title = existing_jigsaw_titles_by_id.get(existing_image.jigsaw_id)
                if existing_image.jigsaw_id is not None and not existing_jigsaw_title:
                    existing_jigsaw_title = db_session.execute(
                        select(Jigsaw.title).where(Jigsaw.id == existing_image.jigsaw_id)
                    ).scalar_one_or_none()
                    if isinstance(existing_jigsaw_title, str):
                        existing_jigsaw_title = existing_jigsaw_title.strip() or None

                if existing_jigsaw_title:
                    duplicate_reason = (
                        f'Image already exists, attached to jigsaw "{existing_jigsaw_title}".'
                    )
                elif existing_image.jigsaw_id is not None:
                    duplicate_reason = (
                        f"Image already exists, attached to jigsaw #{existing_image.jigsaw_id}."
                    )
                else:
                    duplicate_reason = "Image already exists in the image library."

                metadata_backfilled = _backfill_image_capture_metadata(
                    existing_image,
                    item.get("captured_at"),
                    item.get("captured_at_source"),
                    item.get("captured_at_raw"),
                )
                comment_backfilled = _backfill_image_user_comment(existing_image, user_comment)
                uploaded_by_backfilled = _backfill_image_uploaded_by(existing_image, getattr(g.current_user, "id", None))
                issues.append(
                    {
                        "filename": item["filename"] or "(unnamed)",
                        "issue": "duplicate image content already exists",
                        "reason": duplicate_reason,
                        "metadata_backfilled": metadata_backfilled,
                        "comment_backfilled": comment_backfilled,
                        "uploaded_by_backfilled": uploaded_by_backfilled,
                    }
                )
                continue

            if image_sha256 and image_sha256 in created_hashes:
                issues.append(
                    {
                        "filename": item["filename"] or "(unnamed)",
                        "issue": "duplicate image content in current upload batch",
                        "reason": "Image already appears earlier in this upload batch.",
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
                captured_at=item.get("captured_at"),
                captured_at_source=item.get("captured_at_source"),
                captured_at_raw=item.get("captured_at_raw"),
                user_comment=user_comment,
                uploaded_by_user_id=getattr(g.current_user, "id", None),
            )
            created_images.append((image, item["source"]))
            if image_sha256:
                created_hashes.add(image_sha256)

            if associated_jigsaw is not None:
                _maybe_create_diary_entry_from_image(
                    db_session=db_session,
                    jigsaw=associated_jigsaw,
                    image=image,
                    trigger="bulk_upload",
                    created_by_user_id=g.current_user.id,
                )

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
        for created_image, _source in created_images:
            _queue_image_embedding_refresh(created_image.id)
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

    metadata_backfilled_count = sum(1 for issue in issues if issue.get("metadata_backfilled"))

    return _success_response(
        {
            "created_count": len(created_payload),
            "skipped_count": len(issues),
            "metadata_backfilled_count": metadata_backfilled_count,
            "created": created_payload,
            "skipped": issues,
        },
        status_code=201,
    )


@api_v1_bp.patch("/image-library/images/<int:image_id>/assign")
@require_auth
def assign_image_library_item(image_id):
    if not _current_user_has_capability("image.assign"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    if "jigsaw_id" not in payload:
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "jigsaw_id", "issue": "is required"}],
        )

    jigsaw_id, error = _parse_required_positive_integer_or_null(payload.get("jigsaw_id"), "jigsaw_id")
    if error is not None:
        return error

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if jigsaw_id is None:
        if image.jigsaw_id is None:
            return _success_response(_serialize_jigsaw_image(image))

        previous_jigsaw_id = image.jigsaw_id
        image.jigsaw_id = None
        _record_audit_event(
            action="jigsaw.image_unassigned",
            entity_type="jigsaw_image",
            entity_id=image.id,
            payload={
                "previous_jigsaw_id": previous_jigsaw_id,
                "filename": image.filename,
            },
        )
        db_session.commit()

        return _success_response(_serialize_jigsaw_image(image))

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    if image.jigsaw_id is not None and image.jigsaw_id != jigsaw.id:
        return _error_response("conflict", "Image is already assigned to a different jigsaw.", 409)

    if image.jigsaw_id == jigsaw.id:
        return _success_response(_serialize_jigsaw_image(image))

    image.jigsaw_id = jigsaw.id

    _maybe_create_diary_entry_from_image(
        db_session=db_session,
        jigsaw=jigsaw,
        image=image,
        trigger="assignment",
        created_by_user_id=g.current_user.id,
    )

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
@require_auth
def set_image_library_item_tag(image_id):
    if not _current_user_has_capability("image.tag"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

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

    if image.jigsaw_id is not None:
        jigsaw = db_session.get(Jigsaw, image.jigsaw_id)
        if jigsaw is not None:
            _maybe_create_diary_entry_from_image(
                db_session=db_session,
                jigsaw=jigsaw,
                image=image,
                trigger="tag_update",
                created_by_user_id=g.current_user.id,
            )

    _record_audit_event(
        action="jigsaw.image_tag_updated",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={"tag": image.tag},
    )
    db_session.commit()

    return _success_response(_serialize_jigsaw_image(image))


@api_v1_bp.delete("/image-library/images/<int:image_id>")
@require_auth
def delete_image_library_item(image_id):
    if not _current_user_has_capability("image.delete"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if image.jigsaw_id is not None and "administrator" not in g.current_user_roles:
        return _error_response(
            "forbidden",
            "You can only delete unassigned images.",
            403,
        )

    _record_audit_event(
        action="jigsaw.image_deleted",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={
            "jigsaw_id": image.jigsaw_id,
            "tag": image.tag,
            "filename": image.filename,
            "captured_at": image.captured_at.isoformat() if image.captured_at else None,
        },
    )
    db_session.delete(image)
    db_session.commit()

    return _success_response({"id": image_id, "deleted": True})


@api_v1_bp.put("/image-library/images/<int:image_id>/content")
@require_auth
def replace_image_library_item_content(image_id):
    if not _current_user_has_capability("image.upload"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

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
    if not _is_allowed_image_mime_type(mime_type):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "image", "issue": "must be a supported raster image type"}],
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
    captured_at, captured_at_source, captured_at_raw = _extract_image_captured_at(image_data)
    variants = _build_image_variants(image_data, mime_type)
    image.image_data = image_data
    image.mime_type = mime_type
    image.filename = filename
    image.thumbnail_mime_type = variants["thumbnail_mime_type"]
    image.thumbnail_data = variants["thumbnail_data"]
    image.preview_mime_type = variants["preview_mime_type"]
    image.preview_data = variants["preview_data"]
    image.content_version = _normalize_image_content_version(getattr(image, "content_version", 1)) + 1
    if captured_at is not None:
        image.captured_at = captured_at
        image.captured_at_source = captured_at_source
        image.captured_at_raw = captured_at_raw

    _record_audit_event(
        action="jigsaw.image_content_overwritten",
        entity_type="jigsaw_image",
        entity_id=image.id,
        payload={
            "dedupe_hash_preserved": previous_hash,
            "new_content_hash": new_content_hash,
            "mime_type": image.mime_type,
            "size_bytes": len(image_data),
            "captured_at_updated": captured_at is not None,
        },
    )
    db_session.commit()
    _queue_image_embedding_refresh(image.id)

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
            operation=AI_IMAGE_CREATE_OPERATION,
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
        error_payload = None
        if isinstance(error, AiProviderRequestError):
            error_payload = {
                "provider_status_code": error.status_code,
                "provider_response_text": error.response_text,
            }
        _record_ai_usage_event(
            db_session=db_session,
            operation=AI_IMAGE_CREATE_OPERATION,
            image_id=image.id,
            status=AI_USAGE_STATUS_ERROR,
            model=(current_app.config.get("AI_MODEL") or "").strip() or None,
            endpoint_url=(current_app.config.get("AI_ENDPOINT_URL") or "").strip() or None,
            error_code="provider_error",
            error_message=str(error),
            final_cost_usd=Decimal("0"),
            payload=error_payload,
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata extraction failed.", 502)

    normalized_payload, error = _normalize_ai_jigsaw_payload(inference.get("metadata"))
    if error is not None:
        _record_ai_usage_event(
            db_session=db_session,
            operation=AI_IMAGE_CREATE_OPERATION,
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
            payload={
                "raw_metadata": inference.get("metadata"),
                "provider_response": inference.get("provider_response"),
                "provider_response_text": inference.get("provider_response_text"),
            },
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata could not be normalized.", 502)

    jigsaw = Jigsaw(
        title=normalized_payload["title"],
        series_name=normalized_payload["series_name"],
        series_number=normalized_payload["series_number"],
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
        operation=AI_IMAGE_CREATE_OPERATION,
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
        payload={
            "metadata": normalized_payload,
            "raw_metadata": inference.get("metadata"),
            "provider_response": inference.get("provider_response"),
            "provider_response_text": inference.get("provider_response_text"),
            "created_jigsaw_id": jigsaw.id,
        },
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


@api_v1_bp.post("/jigsaws/<int:jigsaw_id>/enrich-from-images")
@require_auth
def enrich_jigsaw_from_images(jigsaw_id):
    if not _current_user_has_capability("jigsaw.enrich"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    overwrite_existing = payload.get("overwrite_existing", False)
    if not isinstance(overwrite_existing, bool):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "overwrite_existing", "issue": "must be a boolean when provided"}],
        )

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    assigned_images = db_session.execute(
        select(JigsawImage)
        .where(JigsawImage.jigsaw_id == jigsaw.id)
        .order_by(JigsawImage.id.asc())
    ).scalars().all()
    if len(assigned_images) == 0:
        return _error_response("conflict", "Jigsaw has no associated images to enrich from.", 409)

    images = [image for image in assigned_images if _is_box_metadata_tag(image.tag)]
    if len(images) == 0:
        return _error_response(
            "conflict",
            "Jigsaw has no box-tagged images to enrich from.",
            409,
        )

    if not current_app.config.get("AI_ENABLED", False):
        return _error_response("conflict", "AI enrichment is disabled in server configuration.", 409)

    if not (current_app.config.get("AI_API_KEY") and current_app.config.get("AI_ENDPOINT_URL") and current_app.config.get("AI_MODEL")):
        return _error_response("conflict", "AI enrichment is not fully configured.", 409)

    budget_usd = _to_decimal(current_app.config.get("AI_DAILY_BUDGET_USD"))
    current_spend = _get_daily_ai_spend(db_session)
    if budget_usd is not None and budget_usd >= Decimal("0") and current_spend >= budget_usd:
        _record_ai_usage_event(
            db_session=db_session,
            operation=AI_JIGSAW_ENRICH_OPERATION,
            image_id=images[0].id if images else None,
            status=AI_USAGE_STATUS_BLOCKED,
            model=(current_app.config.get("AI_MODEL") or "").strip() or None,
            endpoint_url=(current_app.config.get("AI_ENDPOINT_URL") or "").strip() or None,
            error_code="daily_budget_exceeded",
            error_message="Daily AI budget has been reached.",
            final_cost_usd=Decimal("0"),
            payload={"daily_spend_usd": str(current_spend), "daily_budget_usd": str(budget_usd), "jigsaw_id": jigsaw.id},
        )
        db_session.commit()
        return _error_response("conflict", "Daily AI budget has been reached for enrichment.", 409)

    image_descriptors = [
        f"id={image.id}, tag={image.tag or '-'}, filename={image.filename or '-'}"
        for image in images
    ]
    instruction_text = (
        "Use all provided box photos for the same jigsaw (front, back, side, and related box shots) "
        "to extract metadata. Return null for anything uncertain or not visible. "
        "Keep title and series fields separate. "
        f"Current jigsaw fields: title={jigsaw.title!r}, series_name={jigsaw.series_name!r}, "
        f"series_number={jigsaw.series_number!r}, manufacturer={jigsaw.manufacturer!r}, artist={jigsaw.artist!r}, "
        f"piece_count={jigsaw.piece_count!r}, tags={jigsaw.tags!r}, dimensions_cm={jigsaw.dimensions_cm!r}, "
        f"description={jigsaw.description!r}. "
        "Image list: " + "; ".join(image_descriptors)
    )

    try:
        inference = _infer_jigsaw_metadata_from_images(images, instruction_text)
    except RuntimeError as runtime_error:
        error_payload = {
            "jigsaw_id": jigsaw.id,
            "image_ids": [image.id for image in images],
        }
        if isinstance(runtime_error, AiProviderRequestError):
            error_payload["provider_status_code"] = runtime_error.status_code
            error_payload["provider_response_text"] = runtime_error.response_text
        _record_ai_usage_event(
            db_session=db_session,
            operation=AI_JIGSAW_ENRICH_OPERATION,
            image_id=images[0].id if images else None,
            status=AI_USAGE_STATUS_ERROR,
            model=(current_app.config.get("AI_MODEL") or "").strip() or None,
            endpoint_url=(current_app.config.get("AI_ENDPOINT_URL") or "").strip() or None,
            error_code="provider_error",
            error_message=str(runtime_error),
            final_cost_usd=Decimal("0"),
            payload=error_payload,
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata extraction failed.", 502)

    normalized_payload, error = _normalize_ai_jigsaw_payload(inference.get("metadata"))
    if error is not None:
        _record_ai_usage_event(
            db_session=db_session,
            operation=AI_JIGSAW_ENRICH_OPERATION,
            image_id=images[0].id if images else None,
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
            payload={
                "raw_metadata": inference.get("metadata"),
                "provider_response": inference.get("provider_response"),
                "provider_response_text": inference.get("provider_response_text"),
                "jigsaw_id": jigsaw.id,
            },
        )
        db_session.commit()
        return _error_response("bad_gateway", "AI metadata could not be normalized.", 502)

    applied_fields, skipped_fields = _apply_ai_metadata_to_jigsaw(
        jigsaw=jigsaw,
        normalized_payload=normalized_payload,
        overwrite_existing=overwrite_existing,
    )

    usage_event = _record_ai_usage_event(
        db_session=db_session,
        operation=AI_JIGSAW_ENRICH_OPERATION,
        image_id=images[0].id if images else None,
        status=AI_USAGE_STATUS_SUCCESS,
        model=inference.get("model"),
        endpoint_url=inference.get("endpoint_url"),
        prompt_tokens=inference.get("prompt_tokens"),
        completion_tokens=inference.get("completion_tokens"),
        total_tokens=inference.get("total_tokens"),
        provider_cost_usd=inference.get("provider_cost_usd"),
        computed_cost_usd=inference.get("computed_cost_usd"),
        final_cost_usd=inference.get("final_cost_usd") or Decimal("0"),
        payload={
            "jigsaw_id": jigsaw.id,
            "image_ids": [image.id for image in images],
            "overwrite_existing": overwrite_existing,
            "metadata": normalized_payload,
            "raw_metadata": inference.get("metadata"),
            "provider_response": inference.get("provider_response"),
            "provider_response_text": inference.get("provider_response_text"),
            "applied_fields": applied_fields,
            "skipped_fields": skipped_fields,
        },
    )

    _record_audit_event(
        action="jigsaw.enriched_from_images",
        entity_type="jigsaw",
        entity_id=jigsaw.id,
        payload={
            "image_ids": [image.id for image in images],
            "ai_usage_event_id": usage_event.id,
            "overwrite_existing": overwrite_existing,
            "applied_fields": applied_fields,
            "skipped_fields": skipped_fields,
        },
    )
    db_session.commit()

    return _success_response(
        {
            "jigsaw": _serialize_jigsaw(jigsaw),
            "applied_fields": applied_fields,
            "skipped_fields": skipped_fields,
            "ai": {
                "usage_event_id": usage_event.id,
                "prompt_tokens": inference.get("prompt_tokens"),
                "completion_tokens": inference.get("completion_tokens"),
                "total_tokens": inference.get("total_tokens"),
                "final_cost_usd": str(inference.get("final_cost_usd") or Decimal("0")),
            },
        }
    )


@api_v1_bp.get("/images/<int:image_id>/content")
def get_image_content(image_id):
    variant, error = _parse_image_variant(request.args.get("variant"))
    if error is not None:
        return error

    user = _load_current_user()
    if user is None and variant == IMAGE_VARIANT_ORIGINAL:
        return _error_response(
            "authentication_required",
            "Authentication is required for this endpoint.",
            401,
        )

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if image.jigsaw_id is not None:
        jigsaw = db_session.get(Jigsaw, image.jigsaw_id)
        if jigsaw is None:
            return _error_response("not_found", "Jigsaw image was not found.", 404)

        if "administrator" not in getattr(g, "current_user_roles", []) and jigsaw.status == JigsawStatus.RETIRED:
            return _error_response("not_found", "Jigsaw image was not found.", 404)
    elif user is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    return _build_image_content_response(image, variant)


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>/images/<int:image_id>/content")
@require_auth
def get_jigsaw_image_content(jigsaw_id, image_id):
    variant, error = _parse_image_variant(request.args.get("variant"))
    if error is not None:
        return error

    db_session = get_session()
    image = db_session.get(JigsawImage, image_id)
    if image is None or image.jigsaw_id != jigsaw_id:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw image was not found.", 404)

    return _build_image_content_response(image, variant)


@api_v1_bp.get("/jigsaws/<int:jigsaw_id>/diary-entries")
@require_auth
def list_diary_entries(jigsaw_id):
    if not _current_user_has_capability("diary.read"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

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


@api_v1_bp.get("/diary-feed")
@require_auth
def list_diary_feed_entries():
    if not _current_user_has_capability("diary.read"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

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

    selected_jigsaw_id = None
    raw_jigsaw_id = request.args.get("jigsaw_id")
    if raw_jigsaw_id is not None and raw_jigsaw_id.strip() != "":
        try:
            selected_jigsaw_id = int(raw_jigsaw_id)
        except ValueError:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "jigsaw_id", "issue": "must be a positive integer"}],
            )
        if selected_jigsaw_id <= 0:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "jigsaw_id", "issue": "must be a positive integer"}],
            )

    db_session = get_session()

    if selected_jigsaw_id is not None:
        selected_jigsaw = db_session.get(Jigsaw, selected_jigsaw_id)
        if selected_jigsaw is None:
            return _error_response("not_found", "Jigsaw was not found.", 404)
        if "administrator" not in g.current_user_roles and selected_jigsaw.status == JigsawStatus.RETIRED:
            return _error_response("not_found", "Jigsaw was not found.", 404)

    diary_stmt = (
        select(JigsawDiaryEntry, Jigsaw.title)
        .join(Jigsaw, Jigsaw.id == JigsawDiaryEntry.jigsaw_id)
        .order_by(JigsawDiaryEntry.completed_at.desc(), JigsawDiaryEntry.id.desc())
        .limit(limit)
    )
    if "administrator" not in g.current_user_roles:
        diary_stmt = diary_stmt.where(Jigsaw.status != JigsawStatus.RETIRED)
    if selected_jigsaw_id is not None:
        diary_stmt = diary_stmt.where(JigsawDiaryEntry.jigsaw_id == selected_jigsaw_id)

    diary_rows = db_session.execute(diary_stmt).all()
    source_image_ids = {row[0].source_image_id for row in diary_rows if row[0].source_image_id is not None}
    source_images_by_id = {}
    if source_image_ids:
        source_image_rows = db_session.execute(
            select(
                JigsawImage.id,
                JigsawImage.jigsaw_id,
                JigsawImage.tag,
                JigsawImage.filename,
                JigsawImage.mime_type,
                JigsawImage.content_version,
                JigsawImage.captured_at,
                JigsawImage.captured_at_source,
                JigsawImage.user_comment,
                JigsawImage.created_at,
            ).where(JigsawImage.id.in_(source_image_ids))
        ).all()
        source_images_by_id = {
            int(image_id): _serialize_jigsaw_image_fields(
                image_id=image_id,
                jigsaw_id=jigsaw_id,
                tag=tag,
                filename=filename,
                mime_type=mime_type,
                content_version=content_version,
                captured_at=captured_at,
                captured_at_source=captured_at_source,
                user_comment=user_comment,
                created_at=created_at,
            )
            for (
                image_id,
                jigsaw_id,
                tag,
                filename,
                mime_type,
                content_version,
                captured_at,
                captured_at_source,
                user_comment,
                created_at,
            ) in source_image_rows
        }

    diary_feed_items = [
        _serialize_diary_feed_entry(
            entry=entry,
            jigsaw_title=jigsaw_title,
            source_image=source_images_by_id.get(entry.source_image_id),
        )
        for entry, jigsaw_title in diary_rows
    ]

    orphan_feed_items = []
    if selected_jigsaw_id is None:
        normalized_orphan_tag = func.lower(
            func.trim(
                func.replace(
                    func.replace(func.coalesce(JigsawImage.tag, ""), "_", " "),
                    "-",
                    " ",
                )
            )
        )
        orphan_candidates = db_session.execute(
            select(
                JigsawImage.id,
                JigsawImage.jigsaw_id,
                JigsawImage.tag,
                JigsawImage.filename,
                JigsawImage.mime_type,
                JigsawImage.content_version,
                JigsawImage.captured_at,
                JigsawImage.captured_at_source,
                JigsawImage.user_comment,
                JigsawImage.created_at,
            )
            .where(
                JigsawImage.jigsaw_id.is_(None),
                or_(
                    normalized_orphan_tag.like("completed%"),
                    normalized_orphan_tag.like("complete%"),
                ),
            )
            .order_by(func.coalesce(JigsawImage.captured_at, JigsawImage.created_at).desc(), JigsawImage.id.desc())
            .limit(limit)
        ).all()
        orphan_feed_items = []
        for (
            image_id,
            jigsaw_id,
            tag,
            filename,
            mime_type,
            content_version,
            captured_at,
            captured_at_source,
            user_comment,
            created_at,
        ) in orphan_candidates:
            if not _is_completed_image_tag(tag):
                continue
            image_payload = _serialize_jigsaw_image_fields(
                image_id=image_id,
                jigsaw_id=jigsaw_id,
                tag=tag,
                filename=filename,
                mime_type=mime_type,
                content_version=content_version,
                captured_at=captured_at,
                captured_at_source=captured_at_source,
                user_comment=user_comment,
                created_at=created_at,
            )
            orphan_feed_items.append(_serialize_diary_feed_orphan_completed_image(image_payload))

    merged_items = diary_feed_items + orphan_feed_items

    def _sort_key(item):
        completed_at_raw = item.get("completed_at")
        completed_at = datetime.min.replace(tzinfo=timezone.utc)
        if isinstance(completed_at_raw, datetime):
            completed_at = completed_at_raw
        elif isinstance(completed_at_raw, str) and completed_at_raw.strip():
            raw_value = completed_at_raw.strip()
            if raw_value.endswith("Z"):
                raw_value = raw_value[:-1] + "+00:00"
            try:
                completed_at = datetime.fromisoformat(raw_value)
            except ValueError:
                completed_at = datetime.min.replace(tzinfo=timezone.utc)

        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        else:
            completed_at = completed_at.astimezone(timezone.utc)

        return completed_at, int(item.get("id") or 0)

    merged_items.sort(key=_sort_key, reverse=True)

    return _success_response(merged_items[:limit])


@api_v1_bp.post("/jigsaws/<int:jigsaw_id>/diary-entries")
@require_auth
def create_diary_entry(jigsaw_id):
    if not _current_user_has_capability("diary.create"):
        return _error_response(
            "forbidden",
            "You do not have permission to access this resource.",
            403,
        )

    payload, error = _parse_json_object()
    if error is not None:
        return error

    db_session = get_session()
    jigsaw = db_session.get(Jigsaw, jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)
    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Jigsaw was not found.", 404)

    completed_at, error = _parse_optional_iso_datetime(payload.get("completed_at"), "completed_at")
    if error is not None:
        return error
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)
    completed_at = _normalize_datetime_to_utc(completed_at)

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
        created_by_user_id=g.current_user.id,
        completed_at=completed_at,
        difficulty=difficulty,
        notes=notes,
    )
    db_session.add(entry)
    db_session.flush()

    existing_last_completed_at = _normalize_datetime_to_utc(jigsaw.last_completed_at)
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
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)
    serialized = _serialize_diary_entry(entry)

    db_session.delete(entry)
    db_session.flush()

    _recompute_jigsaw_last_completed_at(db_session, jigsaw)

    _record_audit_event(
        action="jigsaw.diary_entry_deleted",
        entity_type="jigsaw_diary_entry",
        entity_id=entry_id,
        payload={"jigsaw_id": serialized["jigsaw_id"]},
    )
    db_session.commit()

    return _success_response(serialized)


@api_v1_bp.patch("/diary-entries/<int:entry_id>")
@require_auth
def update_diary_entry(entry_id):
    payload, error = _parse_json_object()
    if error is not None:
        return error

    db_session = get_session()
    entry = db_session.get(JigsawDiaryEntry, entry_id)
    if entry is None:
        return _error_response("not_found", "Diary entry was not found.", 404)
    jigsaw = db_session.get(Jigsaw, entry.jigsaw_id)
    if jigsaw is None:
        return _error_response("not_found", "Jigsaw was not found.", 404)
    if "administrator" not in g.current_user_roles and jigsaw.status == JigsawStatus.RETIRED:
        return _error_response("not_found", "Diary entry was not found.", 404)

    can_update_any = _current_user_has_capability("diary.update_any")
    can_update_own = _current_user_has_capability("diary.update_own")
    if not can_update_any:
        if not can_update_own or int(entry.created_by_user_id) != int(g.current_user.id):
            return _error_response(
                "forbidden",
                "You do not have permission to access this resource.",
                403,
            )

    mutable_fields = {"completed_at", "difficulty", "notes"}
    if not any(field in payload for field in mutable_fields):
        return _error_response(
            "validation_error",
            "Invalid request payload.",
            422,
            [{"field": "payload", "issue": "must include at least one of: completed_at, difficulty, notes"}],
        )

    if "completed_at" in payload:
        completed_at, error = _parse_optional_iso_datetime(payload.get("completed_at"), "completed_at")
        if error is not None:
            return error
        if completed_at is None:
            return _error_response(
                "validation_error",
                "Invalid request payload.",
                422,
                [{"field": "completed_at", "issue": "must be a valid datetime when provided"}],
            )
    else:
        completed_at = entry.completed_at

    if "difficulty" in payload:
        difficulty, error = _parse_optional_difficulty(payload.get("difficulty"))
        if error is not None:
            return error
    else:
        difficulty = entry.difficulty

    if "notes" in payload:
        notes, error = _validate_optional_text_field(
            payload.get("notes"), field_name="notes", max_length=DIARY_ENTRY_NOTES_MAX_LENGTH
        )
        if error is not None:
            return error
    else:
        notes = entry.notes

    entry.completed_at = completed_at
    entry.difficulty = difficulty
    entry.notes = notes
    entry.updated_by_user_id = g.current_user.id
    db_session.flush()

    _recompute_jigsaw_last_completed_at(db_session, jigsaw)

    _record_audit_event(
        action="jigsaw.diary_entry_updated",
        entity_type="jigsaw_diary_entry",
        entity_id=entry.id,
        payload={
            "jigsaw_id": entry.jigsaw_id,
            "completed_at": entry.completed_at.isoformat(),
            "difficulty": entry.difficulty,
        },
    )
    db_session.commit()

    return _success_response(_serialize_diary_entry(entry))


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

    image_count = db_session.execute(
        select(func.count()).select_from(JigsawImage).where(JigsawImage.jigsaw_id == jigsaw.id)
    ).scalar_one()
    diary_count = db_session.execute(
        select(func.count()).select_from(JigsawDiaryEntry).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id)
    ).scalar_one()
    loan_count = db_session.execute(
        select(func.count()).select_from(Loan).where(Loan.jigsaw_id == jigsaw.id)
    ).scalar_one()

    db_session.execute(sa_delete(JigsawImage).where(JigsawImage.jigsaw_id == jigsaw.id))
    db_session.execute(sa_delete(JigsawDiaryEntry).where(JigsawDiaryEntry.jigsaw_id == jigsaw.id))
    db_session.execute(sa_delete(Loan).where(Loan.jigsaw_id == jigsaw.id))
    db_session.delete(jigsaw)

    _record_audit_event(
        action="jigsaw.deleted",
        entity_type="jigsaw",
        entity_id=jigsaw_id,
        payload={
            "deleted_image_count": int(image_count or 0),
            "deleted_diary_entry_count": int(diary_count or 0),
            "deleted_loan_count": int(loan_count or 0),
        },
    )
    db_session.commit()

    return _success_response({"id": jigsaw_id, "deleted": True})
