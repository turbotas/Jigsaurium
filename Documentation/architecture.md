# Architecture Specification

## Runtime Targets

- Native Windows runtime.
- Native Linux runtime.
- Container runtime (Docker).
- Kubernetes-ready deployment model (manifests/Helm can be added later).

## Environment Hostnames

- Development: `www.dev.jigsaurium.lateral-thought.co.uk`
- Test: `www.test.jigsaurium.lateral-thought.co.uk`
- Production: `www.jigsaurium.lateral-thought.co.uk`

## Technology Baseline

- Backend: Flask.
- ORM: SQLAlchemy 2.x.
- Migrations: Alembic CLI (direct usage, not wrapper).
- Database:
  - MariaDB is the primary test/production baseline.
  - SQLite is permitted for local quick-start/Simple Mode use only.
- DB driver: PyMySQL.
- Frontend: SPA consuming backend JSON APIs.

## Application Shape

- SPA frontend communicates with API endpoints under `/api/v1`.
- Backend responsibilities:
  - authn/authz
  - domain validation
  - persistence and migrations
  - audit logging
- Frontend responsibilities:
  - page state and routing
  - form interactions
  - component rendering (GOV.UK patterns)

## Core Data Entities (initial)

- `users`
  - identity and authentication linkage
  - active/inactive status
- `roles`
  - role name, UNI mapping, and permissions mapping
- `user_roles`
  - many-to-many assignment
- `jigsaws`
  - title, series_name, series_number, manufacturer, artist, dimensions_cm, description, piece_count, condition, status, metadata
- `jigsaw_images`
  - jigsaw_id, tag, filename, mime_type, image_data
  - uploaded_by_user_id attribution for shared-household workflows
  - stored derivative variants for UI performance (thumbnail + preview blobs with mime types)
  - capture metadata, timestamp
- `jigsaw_diary_entries`
  - jigsaw_id, completed_at, difficulty, notes
  - created_by_user_id and updated_by_user_id attribution
- `image_embeddings`
  - image_id, model_key, normalized embedding vector, source-content hash
  - used for visual similarity suggestions (completed-photo reconciliation)
- `image_embedding_jobs`
  - backfill job status/counters for asynchronous embedding generation
- `loans`
  - borrower, jigsaw, checkout date, due date, return date, status
- `audit_events`
  - actor, action, entity type/id, timestamp, payload
- `blocked_ips`
  - blocked client IPs (manual and auto 404-streak), expiry timestamp, source/reason, and hit counters
- `user_sessions`
  - server-side app session registry (session identifier, user, origin IP, auth provider, activity/termination timestamps)
- `database_backups`
  - admin-triggered backup job/history rows (filename, format, status, environment/version tags, storage path, file checksum/size, timestamps)

## Data and Migration Rules

- Connection configured via `DATABASE_URL`.
- Every schema change requires:
  - Alembic `upgrade()` implementation
  - Alembic `downgrade()` implementation
  - migration note in PR
- Use stable naming conventions for constraints/indexes.
- Validate migrations with clean-database `alembic upgrade head`.

## API Design Rules

- Version APIs (`/api/v1/...`).
- Use predictable resource naming and HTTP methods.
- Return structured error payloads for validation and authorization failures.
- Enforce permissions in service/API layer.
- Keep API contract documented as endpoints are added.

## Security and Access Baseline

- Role-based access control from day one.
- Least-privilege defaults.
- Audit all administrative data mutations.
- Keep secrets out of source control; use environment configuration.

## Proxy and Forwarded Header Handling

- Assume all environments run behind one or more reverse proxies.
- Read request origin details (client IP, scheme, host) from exactly one forwarding header family, set by `TRUSTED_PROXY_HEADER`: `X-Forwarded-For`/`-Proto`/`-Host` (default) or RFC7239 `Forwarded`. The other family is ignored, because proxies commonly pass it through from the client unchanged.
- Take right-most values (those added by the nearest proxy), never client-controlled left-most ones.
- Trust forwarded headers only from configured proxy hops/networks.
- Forwarded `proto` and `host` values are ignored when request source is not a trusted proxy.
- Persist both socket remote address and resolved client/proxy chain in request logs.
- Include resolved scheme and host in audit metadata for sensitive actions.
- Canonical host policy is app-configurable via `CANONICAL_HOST_ENFORCEMENT` (`strict` or `off`), with strict mode rejecting non-canonical hosts at the app layer.
