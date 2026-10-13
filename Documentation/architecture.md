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
- Database: MariaDB.
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
  - role name and permissions mapping
- `user_roles`
  - many-to-many assignment
- `jigsaws`
  - title, series_name, series_number, manufacturer, artist, dimensions_cm, description, piece_count, condition, status, metadata
- `jigsaw_images`
  - jigsaw_id, tag, filename, mime_type, image_data, timestamp
- `loans`
  - borrower, jigsaw, checkout date, due date, return date, status
- `audit_events`
  - actor, action, entity type/id, timestamp, payload

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
- Parse RFC7239 `Forwarded` header for request origin details used in logs and audit context.
- Support `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` as compatibility fallbacks.
- Trust forwarded headers only from configured proxy hops/networks.
- Persist both socket remote address and resolved client/proxy chain in request logs.
- Include resolved scheme and host in audit metadata for sensitive actions.
