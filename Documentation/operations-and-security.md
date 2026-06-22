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
- `requirements.txt` points to production dependencies for compatibility.

- `DATABASE_URL`: SQLAlchemy MariaDB connection string.
- `SECRET_KEY`: Flask secret key.
- `APP_ENV`: one of `dev`, `test`, `prod`.
- `LOG_LEVEL`: application logging level.
- `CANONICAL_HOST`: expected public host per environment.
- `TRUSTED_PROXY_CIDRS`: comma-separated proxy CIDRs for header trust.
- `TRUSTED_PROXY_HOPS`: optional fixed proxy depth if CIDR is not used.

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

## Security Baseline

- HTTPS-only in test and production.
- Secure cookie attributes enabled in non-dev environments.
- CSRF protection required for cookie-based auth flows.
- Input validation at API boundary and domain service layers.
- Least-privilege role enforcement at API/service layer.

## Release Checks (manual now, automated later)

- Run functional tests (`pytest -m functional`).
- Run non-functional tests (`pytest -m nonfunctional`).
- Run `alembic upgrade head` in a clean environment.
- Validate API health endpoint and key admin workflow.
- Validate proxy header parsing behavior in each environment.
