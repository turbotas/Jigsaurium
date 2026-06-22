# API Contract Specification (v1)

## Base Rules

- Base path: `/api/v1`.
- Content type: `application/json`.
- All timestamps use UTC ISO 8601 format.
- ID fields are stable, opaque integers in v1.

## Auth and Authorization

- API access requires authenticated user context.
- Session authentication endpoints:
  - `POST /api/v1/auth/login` (public, expects `email` + `password`)
  - `GET /api/v1/auth/me` (authenticated)
  - `POST /api/v1/auth/logout` (authenticated)
- Role checks are enforced server-side for all protected routes.
- Admin-only routes return `403` for authenticated non-admin callers.
- Operational health endpoint `GET /api/v1/health` is allowed without authentication.
- Mutating authenticated endpoints (`POST`, `PATCH`, `DELETE`) require an `X-CSRF-Token` header that matches the session CSRF token.

## Resource Endpoints (initial)

- `GET /api/v1/jigsaws`
- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `PATCH /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/jigsaws`
- `GET /api/v1/jigsaws/{id}`
- `PATCH /api/v1/jigsaws/{id}`
- `DELETE /api/v1/jigsaws/{id}` (retire/archive semantics)
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{id}`
- `GET /api/v1/roles`
- `GET /api/v1/audit-events`

## Filtering, Sorting, Pagination

- Pagination query params: `page` (1-based), `page_size`.
- Sorting query params: `sort` and `order` (`asc` or `desc`).
- Filtering uses explicit query params, for example:
  - `status=available`
  - `piece_count_min=500`
  - `piece_count_max=2000`
  - `q=landscape`

## Standard Success Shape

```json
{
  "data": {},
  "meta": {
    "request_id": "req_abc123"
  }
}
```

## Standard List Shape

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_items": 100,
    "total_pages": 4,
    "request_id": "req_abc123"
  }
}
```

## Standard Error Shape

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request payload.",
    "details": [
      {
        "field": "piece_count",
        "issue": "must be greater than zero"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

## Authentication Payload Notes

- Login request body:

```json
{
  "email": "admin@example.com",
  "password": "example-credential"
}
```

- Login success includes user context and a CSRF token:

```json
{
  "data": {
    "user": {
      "id": 1,
      "email": "admin@example.com",
      "display_name": "Administrator",
      "is_active": true,
      "roles": ["administrator"]
    },
    "csrf_token": "generated-token"
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

- `GET /api/v1/auth/me` also returns `csrf_token` so SPA clients can recover CSRF state after page reload.
- `PATCH /api/v1/auth/me` allows users to update their own `display_name` (username) and change password with `current_password` + `new_password`.
- `PATCH /api/v1/auth/me` rejects email changes.

- User-field validation baseline:
  - `email` must be valid format and `<= 255` chars.
  - `display_name` must be `<= 255` chars and must not contain control chars or angle brackets.
  - `POST /api/v1/users` requires `password` (12-256 chars, no control chars).
  - `PATCH /api/v1/users/{id}` can reset a user's password via optional `password` field (same constraints).
  - Login `password` must be non-empty, `<= 256` chars, and must not contain control chars.
  - Administrators cannot deactivate their own account (`PATCH /api/v1/users/{id}` returns `409` for self-deactivation).

- Audit endpoint notes:
  - `GET /api/v1/audit-events` is admin-only.
  - Optional query param `limit` must be an integer from `1` to `200` (default `50`).

## HTTP Status Rules

- `200` for successful reads and updates.
- `201` for successful creates.
- `400` for malformed requests.
- `401` for unauthenticated access.
- `403` for unauthorized access.
- `404` for unknown resources.
- `409` for state conflicts.
- `422` for validation failures.
- `500` for unhandled server errors.
