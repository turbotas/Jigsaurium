import os


def _parse_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_optional_int(value):
    if value is None or value == "":
        return None
    return int(value)


class Config:
    APP_ENV = os.getenv("APP_ENV", "dev")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CANONICAL_HOST = os.getenv("CANONICAL_HOST", "localhost")
    TRUSTED_PROXY_CIDRS = _parse_csv(os.getenv("TRUSTED_PROXY_CIDRS", ""))
    TRUSTED_PROXY_HOPS = _parse_optional_int(os.getenv("TRUSTED_PROXY_HOPS"))
    SESSION_COOKIE_SECURE = APP_ENV != "dev"
    REMEMBER_COOKIE_SECURE = APP_ENV != "dev"
    PREFERRED_URL_SCHEME = "https" if APP_ENV != "dev" else "http"
