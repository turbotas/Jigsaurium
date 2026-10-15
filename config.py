import os


def _parse_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_optional_int(value):
    if value is None or value == "":
        return None
    return int(value)


def _parse_optional_float(value):
    if value is None or value == "":
        return None
    return float(value)


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = os.getenv("APP_ENV", "dev")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CANONICAL_HOST = os.getenv("CANONICAL_HOST", "localhost")
    TRUSTED_PROXY_CIDRS = _parse_csv(os.getenv("TRUSTED_PROXY_CIDRS", ""))
    TRUSTED_PROXY_HOPS = _parse_optional_int(os.getenv("TRUSTED_PROXY_HOPS"))
    AI_ENABLED = _parse_bool(os.getenv("AI_ENABLED"), default=False)
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_ENDPOINT_URL = os.getenv("AI_ENDPOINT_URL", "")
    AI_MODEL = os.getenv("AI_MODEL", "")
    AI_TIMEOUT_SECONDS = _parse_optional_int(os.getenv("AI_TIMEOUT_SECONDS")) or 60
    AI_DAILY_BUDGET_USD = _parse_optional_float(os.getenv("AI_DAILY_BUDGET_USD"))
    BULK_AI_CREATE_INLINE = _parse_bool(os.getenv("BULK_AI_CREATE_INLINE"), default=False)
    SESSION_COOKIE_SECURE = APP_ENV != "dev"
    REMEMBER_COOKIE_SECURE = APP_ENV != "dev"
    PREFERRED_URL_SCHEME = "https" if APP_ENV != "dev" else "http"
