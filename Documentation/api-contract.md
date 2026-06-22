# API Contract Specification (v1)

## Base Rules

- Base path: `/api/v1`.
- Content type: `application/json`.
- All timestamps use UTC ISO 8601 format.
- ID fields are stable, opaque integers in v1.

## Auth and Authorization

- API access requires authenticated user context.
- Role checks are enforced server-side for all protected routes.
- Admin-only routes return `403` for authenticated non-admin callers.
- Operational health endpoint `GET /api/v1/health` is allowed without authentication.

## Resource Endpoints (initial)

- `GET /api/v1/jigsaws`
- `GET /api/v1/health`
- `POST /api/v1/jigsaws`
- `GET /api/v1/jigsaws/{id}`
- `PATCH /api/v1/jigsaws/{id}`
- `DELETE /api/v1/jigsaws/{id}` (retire/archive semantics)
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{id}`
- `GET /api/v1/roles`

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
