# Operations and Security Specification

## Runtime Configuration

- Git-safe templates:
  - `environments/dev.env.example`
  - `environments/test.env.example`
  - `environments/prod.env.example`
- Sensitive runtime files:
  - `environments/dev.env.local`
  - `environments/test.env.local`
  - `environments/prod.env.local`
- Never commit `*.local` environment files.

## Dependency Profiles

- Use `requirements/prod.txt` for production/runtime-only installs.
- Use `requirements/dev.txt` for developer environments and test execution.
- Use `requirements/known-good-dev.txt` and `requirements/known-good-prod.txt` as constraints files for reproducible installs.
- `requirements.txt` points to production dependencies for compatibility.

- `DATABASE_URL`: SQLAlchemy MariaDB connection string.
- `SECRET_KEY`: Flask secret key.
- `APP_ENV`: one of `dev`, `test`, `prod`.
- `LOG_LEVEL`: application logging level.
- `CANONICAL_HOST`: expected public host per environment.
- `MAX_CONTENT_LENGTH_BYTES`: optional hard cap for inbound request payload size (defaults to `33554432` / 32 MiB).
- `TRUSTED_PROXY_CIDRS`: comma-separated proxy CIDRs for header trust.
- `TRUSTED_PROXY_HOPS`: optional fixed proxy depth if CIDR is not used.
- `AI_ENABLED`: enable/disable AI create-from-image endpoint.
- `AI_API_KEY`: provider API key for vision metadata extraction.
- `AI_ENDPOINT_URL`: AI provider chat/completions-compatible endpoint URL.
- `AI_MODEL`: provider model identifier for image metadata extraction.
- `AI_TIMEOUT_SECONDS`: provider request timeout.
- `AI_DAILY_BUDGET_USD`: optional daily spend limit; when reached, create-from-image requests are blocked.
- `BULK_AI_CREATE_INLINE`: optional boolean for bulk AI create execution mode (`false` = background worker, `true` = inline; test defaults to inline).
- `IMAGE_EMBEDDINGS_ENABLED`: enable/disable CLIP embedding generation and visual match suggestion APIs.
- `IMAGE_EMBEDDING_MODEL_NAME`: CLIP model identifier used for embedding generation (default `openai/clip-vit-base-patch32`).
- `IMAGE_EMBEDDING_MODEL_REVISION`: model revision/tag used with `IMAGE_EMBEDDING_MODEL_NAME`.
- `IMAGE_EMBEDDINGS_INLINE`: optional boolean for embedding generation mode (`false` = background threads, `true` = inline).
- `IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK`: optional boolean to allow deterministic non-CLIP fallback embeddings in test-only environments.
- `IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES`: comma-separated tag prefixes that count as visual-match references (default `box,reference`).

## Canonical Hosts

- Dev: `www.dev.jigsaurium.lateral-thought.co.uk`
- Test: `www.test.jigsaurium.lateral-thought.co.uk`
- Prod: `www.jigsaurium.lateral-thought.co.uk`

## Proxy Header Handling

- Prefer RFC7239 `Forwarded` header when present and trusted.
- Accept `X-Forwarded-*` as compatibility fallback.
- Ignore forwarded headers from untrusted sources.
- Record both raw remote socket address and resolved client chain.

## Request Logging Baseline

- Include these fields in structured logs:
  - `timestamp`
  - `level`
  - `request_id`
  - `method`
  - `path`
  - `status_code`
  - `duration_ms`
  - `host`
  - `scheme`
  - `remote_addr`
  - `client_ip_resolved`
  - `forwarded_chain`
  - `user_id` (if authenticated)
  - `environment`

## AI Usage Logging and Spend Control

- Every create-from-image AI call is recorded in `ai_usage_events` with:
  - operation/status
  - image id and actor
  - model/endpoint
  - prompt/completion/total tokens
  - provider and final USD cost
  - request_id and failure details when applicable
- Spend control evaluates same-day UTC successful AI costs and blocks new create-from-image requests when `AI_DAILY_BUDGET_USD` is reached.

## Security Baseline

- HTTPS-only in test and production.
- Secure cookie attributes enabled in non-dev environments.
- CSRF protection required for cookie-based auth flows.
- Login returns a session CSRF token; clients must send it in `X-CSRF-Token` for authenticated mutating API calls.
- Bootstrap initial admin credentials via `scripts/bootstrap_admin.py`; do not hardcode credentials in source or env templates.
- Input validation at API boundary and domain service layers.
- Least-privilege role enforcement at API/service layer.
- Security response headers are applied to all responses (`Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Cross-Origin-Resource-Policy`).
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` outside dev.
- Login endpoint enforces basic anti-brute-force throttling per client IP and email (15-minute block after repeated failures in the same window).
- Image upload endpoints accept raster image MIME types only (`image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/heic`, `image/heif`); SVG and other active/image-document formats are rejected.

## Release Checks (manual now, automated later)

- Run functional tests (`pytest -m functional`).
- Run non-functional tests (`pytest -m nonfunctional`).
- Run `alembic upgrade head` in a clean environment.
- Validate API health endpoint and key admin workflow.
- Validate proxy header parsing behavior in each environment.

## CI/Test Execution Notes

- CI runs API/core tests on pushes and pull requests.
- CI runs UI smoke tests on pull requests and pushes to `main`/`master`.
- Functional and UI tests use Alembic-migrated test databases (not ORM `create_all`) to keep schema behavior aligned with runtime environments.
- Alembic migration execution fails fast if target URL resolves to in-memory SQLite (`sqlite+pysqlite:///:memory:`) to avoid false-positive migration runs.
