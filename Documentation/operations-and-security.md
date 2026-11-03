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
- Use `requirements/embeddings.txt` for core embedding runtime dependencies (`torch`, `transformers`).
- Production/test deployment target is CPU-only; install PyTorch from the CPU wheel index only and do not install CUDA/NVIDIA runtime packages.
- Use `requirements/known-good-dev.txt` and `requirements/known-good-prod.txt` as constraints files for reproducible installs.
- `requirements.txt` points to production dependencies for compatibility.

- `DATABASE_URL`: SQLAlchemy MariaDB connection string.
- `SECRET_KEY`: Flask secret key.
- `APP_ENV`: one of `dev`, `test`, `prod`.
- `APP_VERSION`: deployed application version (SemVer or release tag such as `v1.2.3`).
- `APP_BUILD_SHA`: source commit SHA for the deployed build.
- `APP_BUILD_TIME`: UTC build timestamp for the deployed build.
- `LOG_LEVEL`: application logging level.
- `CANONICAL_HOST`: expected public host per environment.
- `MAX_CONTENT_LENGTH_BYTES`: optional hard cap for inbound request payload size (defaults to `33554432` / 32 MiB).
- `SESSION_IDLE_TIMEOUT_MINUTES`: authenticated app-session inactivity timeout in minutes (default `120`).
- `TRUSTED_PROXY_CIDRS`: comma-separated proxy CIDRs for header trust.
- `TRUSTED_PROXY_HOPS`: optional fixed proxy depth if CIDR is not used.
- `TRUSTED_CLIENT_CIDRS`: comma-separated client CIDRs exempt from automatic 404-streak IP blocking.
- `STFD_ENABLED`: enable/disable STFD-backed authentication mode.
- `STFD_ALLOW_LOCAL_LOGIN`: optional breakglass/fallback toggle; when `1`, local email/password login remains available while STFD is enabled.
- `STFD_APP_UNI`: STFD application UNI for this environment.
- `STFD_SHARED_KEY`: STFD shared key used to verify incoming JWT assertions.
- `STFD_ASSERT_BASE_URL`: STFD assertion base URL (for example `https://.../stfd/assert`).
- `STFD_REDIRECT_URI`: absolute redirect URI registered with STFD for this environment.
- `STFD_ROLE_UNI_ADMINISTRATOR`: STFD role UNI that maps to local `administrator`.
- `STFD_ROLE_UNI_MEMBER`: STFD role UNI that maps to local `member`.
- `STFD_ROLE_UNI_BORROWER`: STFD role UNI that maps to local `borrower`.
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
- `IMAGE_EMBEDDING_MODEL_LOCAL_PATH`: optional local filesystem path for vendored model artifacts; when set, runtime loads from disk path instead of Hub repo id.
- `IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY`: when `1`, forbid network fetches while loading embeddings (`local_files_only=True`).
- `IMAGE_EMBEDDINGS_WARM_ON_STARTUP`: when `1`, force model load during app startup so first request does not absorb model-load latency.
- `IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR`: when `1`, fail app startup if embedding warm-load fails.
- `IMAGE_EMBEDDINGS_INLINE`: optional boolean for embedding generation mode (`false` = background threads, `true` = inline).
- `IMAGE_EMBEDDINGS_ALLOW_TEST_FALLBACK`: optional boolean to allow deterministic non-CLIP fallback embeddings in test-only environments.
- `IMAGE_EMBEDDING_REFERENCE_TAG_PREFIXES`: comma-separated tag prefixes that count as visual-match references (default `box,reference`).
- `HF_TOKEN`: optional Hugging Face access token for authenticated build-time downloads (runtime should not require this when vendored local model mode is enabled).
- `DB_BACKUP_STORAGE_PATH`: optional absolute/relative directory for in-app SQL backups (defaults to Flask `instance/backups`).
- `DB_BACKUP_COMPRESSION`: backup file compression mode (`gzip` default, `bzip2`, or `none`).
- `DB_BACKUP_BLOB_CHUNK_BYTES`: blob chunk size used when exporting large binary fields as MySQL-compatible SQL variable assembly (default `32768`).
- `DB_BACKUP_MAX_STATEMENT_BYTES`: guardrail maximum SQL statement size for generated backup output (default `4194304`).

## Canonical Hosts

- Dev: `www.dev.jigsaurium.lateral-thought.co.uk`
- Test: `www.test.jigsaurium.lateral-thought.co.uk`
- Prod: `www.jigsaurium.lateral-thought.co.uk`

## Embedding Model Provisioning

- Container images are CPU-only and include embedding dependencies/model vendoring by default.
- For deterministic embedding startup, prefetch the pinned model revision into `IMAGE_EMBEDDING_MODEL_LOCAL_PATH` before enabling embeddings.
- Example (run from repo root):
  - Windows: `.venv\Scripts\python.exe scripts\prefetch_embedding_model.py`
  - Linux/macOS: `.venv/bin/python scripts/prefetch_embedding_model.py`
- Optional: pass `--token` or set `HF_TOKEN` for higher download limits.
- With `IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY=1`, startup and embedding requests fail fast if that local path is missing or incomplete.

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
- Server-side app sessions expire after the configured inactivity window (`SESSION_IDLE_TIMEOUT_MINUTES`, default 120 minutes).
- Login endpoint enforces anti-brute-force throttling per client IP and email (15-minute block after repeated failures in the same window).
- When the login throttle trips, the resolved client IP is persisted in `blocked_ips` for the same block window so the client is blocked across all routes until expiry.
- Runtime request shielding enforces a temporary client-IP ban when a caller produces 5 consecutive `404` responses; ban duration is 24 hours and uses resolved client IP from trusted proxy headers.
- Blocked-IP entries are persisted in `blocked_ips` and can be listed/added/removed by administrators via API/UI.
- Image upload endpoints accept raster image MIME types only (`image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/heic`, `image/heif`); SVG and other active/image-document formats are rejected.

## Release Checks (manual now, automated later)

- Run functional tests (`pytest -m functional`).
- Run non-functional tests (`pytest -m nonfunctional`).
- Run `alembic upgrade head` in a clean environment.
- Validate API health endpoint and key admin workflow.
- Validate proxy header parsing behavior in each environment.

## CI/Test Execution Notes

- CI runs API/core tests on pushes and pull requests (excluding `ui` marker).
- CI runs UI smoke tests on pull requests and pushes to `main`/`master`.
- Embedding runtime tests run in a separate manual/weekly workflow.
- CI workflows enforce a GPU package guard: fail when pip resolves any `nvidia-*` or `cuda-*` package.
- Functional and UI tests use Alembic-migrated test databases (not ORM `create_all`) to keep schema behavior aligned with runtime environments.
- Alembic migration execution fails fast if target URL resolves to in-memory SQLite (`sqlite+pysqlite:///:memory:`) to avoid false-positive migration runs.
