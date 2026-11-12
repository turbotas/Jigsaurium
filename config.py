import os
from datetime import timedelta


def _parse_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_optional_int(value, env_name="value"):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {env_name}: expected integer, got {value!r}") from error


def _parse_optional_float(value, env_name="value"):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {env_name}: expected number, got {value!r}") from error


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_canonical_host_enforcement(value):
    normalized = str(value or "strict").strip().lower()
    if normalized not in {"strict", "off"}:
        raise ValueError(
            "Invalid CANONICAL_HOST_ENFORCEMENT: expected one of strict/off, "
            f"got {value!r}"
        )
    return normalized


class Config:
    APP_ENV = os.getenv("APP_ENV", "dev")
    APP_VERSION = os.getenv("APP_VERSION", "0.0.0-dev")
    APP_BUILD_SHA = os.getenv("APP_BUILD_SHA", "local")
    APP_BUILD_TIME = os.getenv("APP_BUILD_TIME", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CANONICAL_HOST = os.getenv("CANONICAL_HOST", "localhost")
    CANONICAL_HOST_ENFORCEMENT = _parse_canonical_host_enforcement(
        os.getenv("CANONICAL_HOST_ENFORCEMENT", "strict")
    )
    TRUSTED_PROXY_CIDRS = _parse_csv(os.getenv("TRUSTED_PROXY_CIDRS", ""))
    TRUSTED_PROXY_HOPS = _parse_optional_int(os.getenv("TRUSTED_PROXY_HOPS"), env_name="TRUSTED_PROXY_HOPS")
    # Which forwarding header family the proxy is known to set (or overwrite): x-forwarded | forwarded.
    TRUSTED_PROXY_HEADER = os.getenv("TRUSTED_PROXY_HEADER", "x-forwarded")
    TRUSTED_CLIENT_CIDRS = _parse_csv(os.getenv("TRUSTED_CLIENT_CIDRS", ""))
    AI_ENABLED = _parse_bool(os.getenv("AI_ENABLED"), default=False)
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_ENDPOINT_URL = os.getenv("AI_ENDPOINT_URL", "")
    AI_MODEL = os.getenv("AI_MODEL", "")
    AI_TIMEOUT_SECONDS = _parse_optional_int(os.getenv("AI_TIMEOUT_SECONDS"), env_name="AI_TIMEOUT_SECONDS") or 60
    AI_DAILY_BUDGET_USD = _parse_optional_float(os.getenv("AI_DAILY_BUDGET_USD"), env_name="AI_DAILY_BUDGET_USD")
    BULK_AI_CREATE_INLINE = _parse_bool(os.getenv("BULK_AI_CREATE_INLINE"), default=False)
    IMAGE_EMBEDDINGS_ENABLED = _parse_bool(os.getenv("IMAGE_EMBEDDINGS_ENABLED"), default=False)
    IMAGE_EMBEDDING_MODEL_NAME = os.getenv("IMAGE_EMBEDDING_MODEL_NAME", "openai/clip-vit-base-patch32")
    IMAGE_EMBEDDING_MODEL_REVISION = os.getenv("IMAGE_EMBEDDING_MODEL_REVISION", "main")
    IMAGE_EMBEDDING_MODEL_LOCAL_PATH = os.getenv("IMAGE_EMBEDDING_MODEL_LOCAL_PATH", "")
    IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY = _parse_bool(os.getenv("IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY"), default=True)
    IMAGE_EMBEDDINGS_WARM_ON_STARTUP = _parse_bool(os.getenv("IMAGE_EMBEDDINGS_WARM_ON_STARTUP"), default=True)
    IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR = _parse_bool(
        os.getenv("IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR"),
        default=True,
    )
    IMAGE_EMBEDDINGS_INLINE = _parse_bool(os.getenv("IMAGE_EMBEDDINGS_INLINE"), default=False)
    IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK = _parse_bool(
        os.getenv("IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK"),
        default=False,
    )
    IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES = _parse_csv(
        os.getenv("IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES", "box,reference")
    )
    MAX_CONTENT_LENGTH = _parse_optional_int(os.getenv("MAX_CONTENT_LENGTH_BYTES"), env_name="MAX_CONTENT_LENGTH_BYTES") or (32 * 1024 * 1024)
    SESSION_IDLE_TIMEOUT_MINUTES = _parse_optional_int(
        os.getenv("SESSION_IDLE_TIMEOUT_MINUTES"),
        env_name="SESSION_IDLE_TIMEOUT_MINUTES",
    ) or 120
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_SECURE = APP_ENV != "dev"
    REMEMBER_COOKIE_SECURE = APP_ENV != "dev"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https" if APP_ENV != "dev" else "http"
    HSTS_MAX_AGE_SECONDS = _parse_optional_int(
        os.getenv("HSTS_MAX_AGE_SECONDS"),
        env_name="HSTS_MAX_AGE_SECONDS",
    ) or 31536000
    HSTS_INCLUDE_SUBDOMAINS = _parse_bool(os.getenv("HSTS_INCLUDE_SUBDOMAINS"), default=True)
    HSTS_PRELOAD = _parse_bool(os.getenv("HSTS_PRELOAD"), default=False)
    STFD_ENABLED = _parse_bool(os.getenv("STFD_ENABLED"), default=False)
    STFD_ALLOW_LOCAL_LOGIN = _parse_bool(os.getenv("STFD_ALLOW_LOCAL_LOGIN"), default=False)
    STFD_APP_UNI = os.getenv("STFD_APP_UNI", "")
    STFD_SHARED_KEY = os.getenv("STFD_SHARED_KEY", "")
    STFD_ASSERT_BASE_URL = os.getenv("STFD_ASSERT_BASE_URL", "")
    STFD_REDIRECT_URI = os.getenv("STFD_REDIRECT_URI", "")
    STFD_ROLE_UNI_ADMINISTRATOR = os.getenv("STFD_ROLE_UNI_ADMINISTRATOR", "")
    STFD_ROLE_UNI_MEMBER = os.getenv("STFD_ROLE_UNI_MEMBER", "")
    STFD_ROLE_UNI_BORROWER = os.getenv("STFD_ROLE_UNI_BORROWER", "")
    DB_BACKUP_STORAGE_PATH = os.getenv("DB_BACKUP_STORAGE_PATH", "")
    DB_BACKUP_COMPRESSION = os.getenv("DB_BACKUP_COMPRESSION", "gzip")
    DB_BACKUP_BLOB_CHUNK_BYTES = _parse_optional_int(
        os.getenv("DB_BACKUP_BLOB_CHUNK_BYTES"),
        env_name="DB_BACKUP_BLOB_CHUNK_BYTES",
    ) or (32 * 1024)
    DB_BACKUP_MAX_STATEMENT_BYTES = _parse_optional_int(
        os.getenv("DB_BACKUP_MAX_STATEMENT_BYTES"),
        env_name="DB_BACKUP_MAX_STATEMENT_BYTES",
    ) or (4 * 1024 * 1024)
