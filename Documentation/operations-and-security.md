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

## Simple Mode Default Profile (M2 Step 2.1)

For quick-start/local onboarding, Simple Mode defaults are:

- `STFD_ENABLED=0`
- `AI_ENABLED=0`
- `IMAGE_EMBEDDINGS_ENABLED=0`

With these defaults, STFD/AI/embedding credentials are optional and may be blank in local templates.

See `Documentation/simple-mode.md` for the full feature-flag matrix and UI behavior expectations.

## Dependency Profiles

- Use `requirements/prod.txt` for production/runtime-only installs.
- Use `requirements/dev.txt` for developer environments and test execution.
- Use `requirements/embeddings.txt` for core embedding runtime dependencies (`torch`, `transformers`).
- Core image runtime depends on Pillow plus `pillow-heif` so HEIF/HEIC uploads can be decoded for metadata extraction and derivative generation.
- Production/test deployment target is CPU-only; install PyTorch from the CPU wheel index only and do not install CUDA/NVIDIA runtime packages.
- Use `requirements/known-good-dev.txt` and `requirements/known-good-prod.txt` as constraints files for reproducible installs.
- `requirements.txt` points to production dependencies for compatibility.

- `DATABASE_URL`: SQLAlchemy MariaDB connection string.
- `AUTO_MIGRATE`: when `1`, container entrypoint runs `alembic upgrade head` on startup before launching the app process.
- `SECRET_KEY`: Flask secret key.
- `APP_ENV`: one of `dev`, `test`, `prod`.
- `APP_VERSION`: deployed application version (SemVer or release tag such as `v1.2.3`).
- `APP_BUILD_SHA`: source commit SHA for the deployed build.
- `APP_BUILD_TIME`: UTC build timestamp for the deployed build.
- `LOG_LEVEL`: application logging level.
- `CANONICAL_HOST`: expected public host per environment.
- `CANONICAL_HOST_ENFORCEMENT`: host-policy mode (`strict` to reject non-canonical hosts with HTTP 421, `off` to disable app-layer host checks).
- `HSTS_MAX_AGE_SECONDS`: HSTS `max-age` value for HTTPS responses in test/prod (default `31536000`).
- `HSTS_INCLUDE_SUBDOMAINS`: include `includeSubDomains` in HSTS header when truthy (default `1`).
- `HSTS_PRELOAD`: include `preload` token in HSTS header when truthy (default `0`).
- `MAX_CONTENT_LENGTH_BYTES`: optional hard cap for inbound request payload size (defaults to `33554432` / 32 MiB).
- `SESSION_IDLE_TIMEOUT_MINUTES`: authenticated app-session inactivity timeout in minutes (default `120`).
- `TRUSTED_PROXY_CIDRS`: comma-separated proxy CIDRs for header trust.
- `TRUSTED_PROXY_HOPS`: optional fixed proxy depth if CIDR is not used.
- `TRUSTED_PROXY_HEADER`: which forwarding header family the proxy sets or overwrites: `x-forwarded` (default; `X-Forwarded-For`/`-Proto`/`-Host`) or `forwarded` (RFC7239 `Forwarded`). Only that family is read; the other is ignored.
- `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `GUNICORN_GRACEFUL_TIMEOUT`, `GUNICORN_KEEPALIVE`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_MAX_REQUESTS_JITTER`, `GUNICORN_BIND`, `GUNICORN_LOG_LEVEL`: optional overrides for the container's WSGI server (defaults in `gunicorn.conf.py`).
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

Host enforcement policy:

- `CANONICAL_HOST_ENFORCEMENT=strict` (recommended for deployed environments) rejects requests whose host does not match `CANONICAL_HOST`.
- `CANONICAL_HOST_ENFORCEMENT=off` allows non-canonical hosts (useful for local contributor workflows).

## Embedding Model Provisioning

- Container images are CPU-only and include embedding dependencies/model vendoring by default.
- For deterministic embedding startup, prefetch the pinned model revision into `IMAGE_EMBEDDING_MODEL_LOCAL_PATH` before enabling embeddings.
- Example (run from repo root):
  - Windows: `.venv\Scripts\python.exe scripts\prefetch_embedding_model.py`
  - Linux/macOS: `.venv/bin/python scripts/prefetch_embedding_model.py`
- Optional: pass `--token` or set `HF_TOKEN` for higher download limits.
- With `IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY=1`, startup and embedding requests fail fast if that local path is missing or incomplete.
- Development exception: when `APP_ENV=dev`, startup warm-load logs a warning and continues if the configured local model path is missing, even when startup fail-fast is enabled. This prevents local boot failures after env-file changes; embedding endpoints remain unavailable until the model is prefetched or embeddings are disabled.

## Proxy Header Handling

- Trust exactly one forwarding header family, chosen by `TRUSTED_PROXY_HEADER`:
  - `x-forwarded` (default): read `X-Forwarded-For`, `X-Forwarded-Proto` and `X-Forwarded-Host`; ignore `Forwarded`.
  - `forwarded`: read RFC7239 `Forwarded` (`for`, `proto`, `host`); ignore `X-Forwarded-*`.
- Why one family only: most proxies set one family and pass the other through from the client unchanged. Reading both (or preferring `Forwarded` when present) lets any client choose its own IP, host and scheme, which defeats login throttling and IP bans and lets a client get someone else's IP banned.
- Use `forwarded` only when the proxy overwrites `Forwarded` on every request (see the Nginx example below).
- To find out what the proxy does without access to its config, sign in as an administrator through the public URL and use **Service Health > Reverse proxy headers > Check proxy headers**. It sends fake forwarding headers and reports which ones the proxy passed through, appended to, overwrote or removed, plus the safe `TRUSTED_PROXY_HEADER` value. Re-run it after any proxy change.
- Client IP: the right-most address in the chain that is not a trusted proxy (CIDR mode), or the `TRUSTED_PROXY_HOPS`-th address from the right (hops mode).
- `proto`/`host`: the right-most value, which is the one the nearest proxy added.
- Ignore forwarded headers from untrusted sources.
- Record both raw remote socket address and resolved client chain.
- Trust forwarded `proto`/`host` values only when request source matches `TRUSTED_PROXY_CIDRS` (or configured `TRUSTED_PROXY_HOPS` mode).

## Security Header Policy

- CSP uses nonce-based inline script allowlisting (`script-src 'self' 'nonce-...'`) and does not permit `unsafe-inline` scripts.
- HSTS is applied on HTTPS responses in test/prod with default policy:
  - `max-age=31536000`
  - `includeSubDomains`
  - `preload` disabled by default (enable via `HSTS_PRELOAD=1` only after preload-readiness review).

## Reverse-Proxy Hardening Checklist

- Terminate TLS at the proxy; do not expose direct public HTTP to the Flask process.
- Configure `Strict-Transport-Security` at the proxy edge for public HTTPS hosts (test/prod).
- Restrict direct network access to the Flask service (private network / firewall allowlist / loopback-only bind where possible).
- Ensure proxy overwrites inbound forwarding headers (do not pass client-supplied values through unchanged).
- Set `TRUSTED_PROXY_HEADER` to the header family the proxy actually overwrites. With only `$proxy_add_x_forwarded_for` (the common default, including Nginx Proxy Manager), keep `x-forwarded`.
- Also clear the header family you are not using, so it never reaches the app: for example `proxy_set_header Forwarded "";` when using `x-forwarded`.
- Bind the published container port to the address the proxy uses (for example `"192.168.1.10:5000:5000"`), not all interfaces, and keep `TRUSTED_PROXY_CIDRS` to the proxy's own address(es) rather than whole LAN or Docker ranges.
- Set `TRUSTED_PROXY_CIDRS` to exact proxy CIDR(s) used by this environment.
- Keep `CANONICAL_HOST` and `CANONICAL_HOST_ENFORCEMENT` aligned with deployed hostname policy.
- Keep Flask app behind the proxy boundary; do not publish Flask listener directly to the internet.

Example Nginx forwarding block (safe overwrite pattern):

```nginx
location / {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Forwarded "for=$remote_addr;proto=$scheme;host=$host";

    proxy_pass http://jigsaurium_app;
}
```

`TRUSTED_PROXY_CIDRS` examples:

- Single reverse proxy host: `TRUSTED_PROXY_CIDRS=192.168.100.12/32`
- Internal proxy subnet: `TRUSTED_PROXY_CIDRS=10.20.30.0/24`

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
- In non-dev environments (`APP_ENV=test|prod`), startup fails when `SECRET_KEY` is missing, default/placeholder, or shorter than 32 characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it signs everyone out.
- The container runs gunicorn (`gunicorn.conf.py`: one process, threaded, request timeouts and header limits), never the Flask/Werkzeug development server.
- Server-side app sessions expire after the configured inactivity window (`SESSION_IDLE_TIMEOUT_MINUTES`, default 120 minutes).
- Login endpoint enforces anti-brute-force throttling per client IP and email (15-minute block after 10 failures in a 15-minute window).
- Login endpoint also limits each email across all client IPs: 30 failures in a 15-minute window block further attempts for that email for 15 minutes (IP addresses are not blocked by this limit). A successful login clears both counters for that email.
- Failed logins for unknown or password-less accounts still run a password-hash check, so response time does not reveal whether an email has an account.
- When the login throttle trips, the resolved client IP is persisted in `blocked_ips` for the same block window so the client is blocked across all routes until expiry.
- Runtime request shielding enforces a temporary client-IP ban when a caller produces 5 consecutive `404` responses; ban duration is 24 hours and uses resolved client IP from trusted proxy headers.
- Blocked-IP entries are persisted in `blocked_ips` and can be listed/added/removed by administrators via API/UI.
- Image upload endpoints accept raster image MIME types only (`image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/heic`, `image/heif`); SVG and other active/image-document formats are rejected.
- The declared type is not trusted: uploaded bytes (including zip entries) must decode as one of those formats, and the stored MIME type is the detected one.
- Unauthenticated callers only receive re-encoded thumbnail/preview derivatives. When a derivative could not be generated, guests get `404` rather than the original upload bytes.

## Release Checks (manual now, automated later)

- Run functional tests (`pytest -m functional`).
- Run non-functional tests (`pytest -m nonfunctional`).
- Run `alembic upgrade head` in a clean environment.
- Validate API health endpoint and key admin workflow.
- Validate proxy header parsing behavior in each environment.
- Validate HSTS on public HTTPS host:
  - `curl -I https://<public-host>/ | findstr Strict-Transport-Security` (Windows)
  - `curl -I https://<public-host>/ | grep -i Strict-Transport-Security` (Linux/macOS)
- Validate CSP no-inline-script policy:
  - inspect `Content-Security-Policy` response header and confirm `script-src` includes nonce and excludes `unsafe-inline`.

## CI/Test Execution Notes

- CI runs API/core tests on pushes and pull requests (excluding `ui` marker).
- CI runs UI smoke tests on pull requests and pushes to `main`/`master`.
- Embedding runtime tests run in a separate manual/weekly workflow.
- CI workflows enforce a GPU package guard: fail when pip resolves any `nvidia-*` or `cuda-*` package.
- Functional and UI tests use Alembic-migrated test databases (not ORM `create_all`) to keep schema behavior aligned with runtime environments.
- Alembic migration execution fails fast if target URL resolves to in-memory SQLite (`sqlite+pysqlite:///:memory:`) to avoid false-positive migration runs.

## Test Quality Statement (M3 Step 3.2)

Jigsaurium uses a **scope-based test quality policy** rather than a global percentage-only coverage gate.

### Minimum policy for changes

- Every behavior change must include tests at the level where the behavior is enforced:
  - API/domain rule changes: functional API tests.
  - UI interaction changes: UI smoke tests (or functional coverage when UI-only automation is not practical).
  - Migration/schema changes: migration validation via Alembic upgrade path checks.
- Bug fixes must include a regression test that fails before the fix and passes after it.
- New public-facing or admin critical-path workflows must have at least one end-to-end happy-path test.

### CI baseline required for merge readiness

- `API and Core Tests` must pass (`pytest -m "not ui"`).
- `UI Smoke Tests` must pass for pull requests and default-branch pushes.
- `Embedding Runtime Tests` remain a separate manual/weekly guardrail and are required before release-candidate sign-off when embedding behavior changed.

### Coverage target posture

- Preferred direction: maintain or improve meaningful coverage over time, especially around authn/authz, audit logging, jigsaw/diary/image-library workflows, and migrations.
- Temporary exceptions are allowed only when documented in the relevant issue/PR with follow-up work explicitly tracked.
