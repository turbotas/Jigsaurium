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
- `GET /api/v1/loans`
- `POST /api/v1/loans`
- `GET /api/v1/jigsaws/{id}/images`
- `POST /api/v1/jigsaws/{id}/images`
- `GET /api/v1/jigsaws/{id}/images/{image_id}/content`
- `GET /api/v1/image-library/images`
- `POST /api/v1/image-library/uploads`
- `PATCH /api/v1/image-library/images/{image_id}/assign`
- `POST /api/v1/image-library/images/{image_id}/create-jigsaw`
- `GET /api/v1/images/{image_id}/content`
- `GET /api/v1/jigsaws/{id}/diary-entries`
- `POST /api/v1/jigsaws/{id}/diary-entries`
- `DELETE /api/v1/diary-entries/{id}`

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

- Loan endpoint notes:
  - `GET /api/v1/loans` is admin-only in the initial administrative rollout.
  - `POST /api/v1/loans` is admin-only in the initial administrative rollout.
  - `POST /api/v1/loans` request body requires:
    - `borrower_user_id` (positive integer)
    - `jigsaw_id` (positive integer)
  - `borrower_user_id` may reference an active user with `borrower` or `administrator` role.
  - Loan checkout sets `checked_out_at` to current UTC time.
  - Loan checkout sets `due_at` to four weeks (28 days) after `checked_out_at`.
  - Loan checkout returns `409` when the target jigsaw is not currently available.
  - Loan checkout updates jigsaw status to `on_loan`.

- Jigsaw metadata notes:
  - `POST /api/v1/jigsaws` allows empty values for all jigsaw fields; omitted/blank `status` defaults to `available`.
  - Duplicate `title` values are allowed.
  - Jigsaw payloads now support optional fields: `manufacturer`, `artist`, `dimensions_cm`, `description`, `last_completed_at`.
  - `last_completed_at` uses UTC ISO 8601 format.

- Jigsaw image endpoint notes:
  - `GET /api/v1/jigsaws/{id}/images` is admin-only.
  - `POST /api/v1/jigsaws/{id}/images` is admin-only.
  - `POST /api/v1/jigsaws/{id}/images` expects multipart form data:
    - `tag` (optional string, defaults to `untagged` when omitted)
    - `image` (required file, image MIME type)
  - Uploaded images are stored in the database for v1.
  - Image content hash (`SHA-256`) is used for duplicate suppression; uploading identical bytes returns the existing image instead of creating a duplicate row.
  - `GET /api/v1/jigsaws/{id}/images/{image_id}/content` remains supported for jigsaw-associated images.

- Image library endpoint notes:
  - `GET /api/v1/image-library/images` is admin-only and returns recent images across the full library.
  - `GET /api/v1/image-library/images` optional query param `limit` must be an integer from `1` to `500` (default `200`).
  - `POST /api/v1/image-library/uploads` is admin-only and expects multipart form data:
    - `files` (one or more uploads; each may be an image file or a `.zip` archive containing image files)
    - `jigsaw_id` (optional positive integer association)
    - `tag` (optional string, defaults to `untagged`)
  - Images uploaded through the image-library endpoint may be unassigned (`jigsaw_id = null`).
  - `POST /api/v1/image-library/uploads` returns a summary: `created_count`, `skipped_count`, and per-item `created` / `skipped` details.
  - Hash duplicate handling applies to bulk imports too: duplicate image bytes are skipped and reported in `skipped`.
  - `PATCH /api/v1/image-library/images/{image_id}/assign` is admin-only and requires JSON body `{ "jigsaw_id": <positive integer> }`.
  - `PATCH /api/v1/image-library/images/{image_id}/assign` assigns an image to one jigsaw; reassignment to a different jigsaw returns `409`.
  - `POST /api/v1/image-library/images/{image_id}/create-jigsaw` is admin-only and creates a new jigsaw from AI-extracted image metadata.
  - `POST /api/v1/image-library/images/{image_id}/create-jigsaw` only works for unassigned images; assigned images return `409`.
  - Successful create-from-image sets the associated image tag to `Box`.
  - AI extraction expects these metadata keys: `title`, `manufacturer`/`publisher`, `artist`, `piece_count`, `tags`, `dimensions_cm`, `description`.
  - AI usage is cost-tracked per call (`ai_usage_events`) with token usage and final USD cost.
  - Daily AI spend guardrail: when configured budget is reached, create-from-image requests return `409` and are blocked before provider calls.
  - `GET /api/v1/images/{image_id}/content` returns binary image content for authenticated users, including unassigned library images.
  - Bulk uploads write `jigsaw.image_bulk_uploaded` audit events.
  - Image assignment writes `jigsaw.image_assigned` audit events.
  - Create-from-image writes `jigsaw.created_from_image` audit events.

- Diary endpoint notes:
  - `GET /api/v1/jigsaws/{id}/diary-entries` requires authentication; retired jigsaws return `404` for non-admin callers. Entries are ordered by `completed_at` descending.
  - `POST /api/v1/jigsaws/{id}/diary-entries` is admin-only. Request body fields are all optional:
    - `completed_at` (UTC ISO 8601 datetime; defaults to current UTC time)
    - `difficulty` (integer 1-5, or empty)
    - `notes` (string up to 4000 characters, no control characters)
  - Creating an entry moves the parent jigsaw's `last_completed_at` forward when the entry is newer.
  - `DELETE /api/v1/diary-entries/{id}` is admin-only and returns the deleted entry; the parent jigsaw's `last_completed_at` is recomputed from remaining entries.
  - Diary entry create/delete write audit events (`jigsaw.diary_entry_created`, `jigsaw.diary_entry_deleted`).

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
