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
- Role/capability checks are enforced server-side for all protected routes.
- Authorization is capability-driven in v1; route handlers validate required capabilities and return `403` for authenticated callers that lack them.
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
- `GET /api/v1/jigsaws/thumbnail-images`
- `PATCH /api/v1/jigsaws/{id}`
- `DELETE /api/v1/jigsaws/{id}` (retire/archive semantics)
- `DELETE /api/v1/jigsaws/{id}/permanent` (hard-delete semantics)
- `POST /api/v1/jigsaws/{id}/enrich-from-images`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{id}`
- `GET /api/v1/roles`
- `GET /api/v1/audit-events`
- `GET /api/v1/ai-usage/diagnostics`
- `GET /api/v1/loans`
- `POST /api/v1/loans`
- `POST /api/v1/loans/{id}/return`
- `GET /api/v1/jigsaws/{id}/images`
- `POST /api/v1/jigsaws/{id}/images`
- `GET /api/v1/jigsaws/{id}/images/{image_id}/content`
- `GET /api/v1/image-library/images`
- `POST /api/v1/image-library/uploads`
- `DELETE /api/v1/image-library/images/{image_id}`
- `PATCH /api/v1/image-library/images/{image_id}/assign`
- `PATCH /api/v1/image-library/images/{image_id}/tag`
- `PUT /api/v1/image-library/images/{image_id}/content`
- `POST /api/v1/image-library/images/{image_id}/create-jigsaw`
- `POST /api/v1/image-library/bulk-create-jigsaws`
- `POST /api/v1/image-library/bulk-create-jigsaws/unassigned-box`
- `GET /api/v1/image-library/bulk-create-jigsaws/{job_id}`
- `GET /api/v1/image-library/bulk-create-jigsaws/{job_id}/items`
- `POST /api/v1/image-embeddings/backfill`
- `GET /api/v1/image-embeddings/backfill/{job_id}`
- `GET /api/v1/image-library/images/{image_id}/match-suggestions`
- `GET /api/v1/images/{image_id}/content`
- `GET /api/v1/jigsaws/{id}/diary-entries`
- `GET /api/v1/diary-feed`
- `POST /api/v1/jigsaws/{id}/diary-entries`
- `PATCH /api/v1/diary-entries/{id}`
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
      "roles": ["administrator"],
      "capabilities": ["audit.read", "diary.create", "diary.update_any"]
    },
    "csrf_token": "generated-token"
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

- `GET /api/v1/auth/me` also returns `csrf_token` so SPA clients can recover CSRF state after page reload.
- Auth payload user objects include a derived `capabilities` array to support SPA feature-gating without hardcoding role names.
- Current role capability defaults:
  - `administrator`: full administrative capabilities, including user/loan/AI management and destructive actions.
  - `member`: shared-collection capabilities for jigsaw create/read/update/enrich, diary create/read/update-own, image upload/library/tag/assign, and audit read.
  - `borrower`: legacy compatibility role that currently maps to the same capabilities as `member`.
- `PATCH /api/v1/auth/me` allows users to update their own `display_name` (username) and change password with `current_password` + `new_password`.
- `PATCH /api/v1/auth/me` rejects email changes.
- Repeated failed login attempts for the same client/IP + email are rate-limited; blocked attempts return `429` and include `Retry-After`.
- Repeated request probing that yields 5 consecutive `404` responses from the same client IP triggers a 24-hour temporary block; blocked requests return `429` and include `Retry-After`.

- User-field validation baseline:
  - `email` must be valid format and `<= 255` chars.
  - `display_name` must be `<= 255` chars and must not contain control chars or angle brackets.
  - `POST /api/v1/users` requires `password` (12-256 chars, no control chars).
  - `PATCH /api/v1/users/{id}` can reset a user's password via optional `password` field (same constraints).
  - Login `password` must be non-empty, `<= 256` chars, and must not contain control chars.
  - Administrators cannot deactivate their own account (`PATCH /api/v1/users/{id}` returns `409` for self-deactivation).

- Audit endpoint notes:
  - `GET /api/v1/audit-events` requires `audit.read` capability.
  - Administrators receive unfiltered audit events; non-admin callers are scoped to events where `actor_user_id` matches the caller.
  - Optional pagination query params:
    - `page` (integer `>= 1`, default `1`)
    - `page_size` (integer `1..200`, default `25`)
  - Legacy query param `limit` is still accepted as an alias for `page_size`.
  - Response uses standard list `meta` fields (`page`, `page_size`, `total_items`, `total_pages`).

- AI diagnostics endpoint notes:
  - `GET /api/v1/ai-usage/diagnostics` is admin-only.
  - Optional pagination query params for the `recent_calls` list:
    - `page` (integer `>= 1`, default `1`)
    - `page_size` (integer `1..200`, default `25`)
  - Legacy query param `limit` is still accepted as an alias for `page_size`.
  - Response includes:
    - spend/call/token summaries for `today`, `last_7_days`, and `last_30_days`
    - 30-day grouped breakdowns by operation and by model
    - recent call diagnostics including status, token/cost fields, request id, image metadata, provider error hints (for example parsed HTTP status from provider error text), and stored per-call payload details for troubleshooting
    - `recent_calls_pagination` metadata (`page`, `page_size`, `total_items`, `total_pages`)

- Loan endpoint notes:
  - `GET /api/v1/loans` is admin-only in the initial administrative rollout.
  - `POST /api/v1/loans` is admin-only in the initial administrative rollout.
  - `POST /api/v1/loans/{id}/return` is admin-only and closes an active/overdue loan.
  - `POST /api/v1/loans` request body requires:
    - `borrower_user_id` (positive integer)
    - `jigsaw_id` (positive integer)
  - `borrower_user_id` may reference an active user with `member`, `borrower` (legacy), or `administrator` role.
  - Loan checkout sets `checked_out_at` to current UTC time.
  - Loan checkout sets `due_at` to four weeks (28 days) after `checked_out_at`.
  - Loan checkout returns `409` when the target jigsaw is not currently available.
  - Loan checkout updates jigsaw status to `on_loan`.
  - Loan return sets `returned_at` to current UTC time and sets loan status to `returned`.
  - Loan return sets jigsaw status to `available` when the linked jigsaw is currently `on_loan`.
  - Loan return returns `409` when the loan is not active/overdue.

- Jigsaw metadata notes:
  - `GET /api/v1/jigsaws` supports optional pagination query params `page` and `page_size` (or legacy `limit` alias).
  - When pagination params are provided, response includes standard list `meta` fields (`page`, `page_size`, `total_items`, `total_pages`).
  - `GET /api/v1/jigsaws/thumbnail-images` returns one preferred image per jigsaw for fast stock-list thumbnail rendering.
  - `POST /api/v1/jigsaws` requires `jigsaw.create` capability and allows empty values for all jigsaw fields; omitted/blank `status` defaults to `available`.
  - `PATCH /api/v1/jigsaws/{id}` requires `jigsaw.update` capability.
  - Non-admin callers cannot set jigsaw status to `retired` through `PATCH /api/v1/jigsaws/{id}`.
  - Duplicate `title` values are allowed.
  - Jigsaw payloads now support optional fields: `series_name`, `series_number`, `manufacturer`, `artist`, `dimensions_cm`, `description`, `last_completed_at`.
  - `last_completed_at` uses UTC ISO 8601 format.
  - `DELETE /api/v1/jigsaws/{id}` is administrator-only and retires the jigsaw (soft delete).
  - `DELETE /api/v1/jigsaws/{id}/permanent` is administrator-only and permanently removes the jigsaw and deletes linked images, diary entries, and loans.

- Jigsaw image endpoint notes:
  - `GET /api/v1/jigsaws/{id}/images` requires `image.manage_library` capability.
  - `POST /api/v1/jigsaws/{id}/images` requires `image.upload` capability.
  - Non-admin callers receive `404` for retired jigsaws on these routes.
  - `POST /api/v1/jigsaws/{id}/images` expects multipart form data:
    - `tag` (optional string, defaults to `untagged` when omitted)
    - `comment` (optional string up to 2000 chars; stored as user feedback on the image)
    - `image` (required file, image MIME type)
  - Accepted upload MIME types are raster formats only: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/heic`, `image/heif`.
  - SVG and other active image-document formats are rejected.
  - Uploaded images are stored in the database for v1.
  - Image payloads include derivative URLs:
    - `content_url` (original)
    - `thumbnail_url` (`variant=thumbnail`, optimized for inventory/list tables)
    - `preview_url` (`variant=preview`, optimized for hover/magnify preview)
  - Image content hash (`SHA-256`) is used for duplicate suppression; uploading identical bytes returns the existing image instead of creating a duplicate row.
  - Image payloads include optional capture metadata: `captured_at` (UTC ISO 8601) and `captured_at_source`.
  - Image payloads include optional `user_comment` (caller-uploaded feedback/notes for that image).
  - `GET /api/v1/jigsaws/{id}/images/{image_id}/content` remains supported for jigsaw-associated images.

- Image library endpoint notes:
  - `GET /api/v1/image-library/images` requires `image.manage_library` capability and returns recent images across the full library.
  - `GET /api/v1/image-library/images` supports optional pagination query params:
    - `page` (integer `>= 1`, default `1`)
    - `page_size` (integer `1..500`, default `25`)
  - Legacy query param `limit` is still accepted as an alias for `page_size`.
  - Response uses standard list `meta` fields (`page`, `page_size`, `total_items`, `total_pages`).
  - `POST /api/v1/image-library/uploads` requires `image.upload` capability and expects multipart form data:
    - `files` (one or more uploads; each may be an image file or a `.zip` archive containing image files)
    - `jigsaw_id` (optional positive integer association)
    - `tag` (optional string, defaults to `untagged`)
    - `comment` (optional string up to 2000 chars; applied to created image rows)
  - Images uploaded through the image-library endpoint may be unassigned (`jigsaw_id = null`).
  - Accepted upload MIME types are raster formats only: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/heic`, `image/heif`.
  - SVG and other active image-document formats are rejected.
  - `POST /api/v1/image-library/uploads` returns a summary: `created_count`, `skipped_count`, `metadata_backfilled_count`, and per-item `created` / `skipped` details.
  - Hash duplicate handling applies to bulk imports too: duplicate image bytes are skipped and reported in `skipped`.
  - Duplicate-image skips may still backfill missing capture metadata on the existing image record when newly uploaded bytes include EXIF capture time.
  - `PATCH /api/v1/image-library/images/{image_id}/assign` requires `image.assign` capability and JSON body with `jigsaw_id`:
    - positive integer to assign
    - `null` to unassign
  - `PATCH /api/v1/image-library/images/{image_id}/assign` assigns an image to one jigsaw; reassignment to a different jigsaw returns `409`.
  - `DELETE /api/v1/image-library/images/{image_id}` is administrator-only and permanently deletes the image record.
  - `PATCH /api/v1/image-library/images/{image_id}/tag` requires `image.tag` capability and updates image tag/classification (for example `Box`, `Completed`) even when image is unassigned.
  - Known built-in tag variants are normalized to canonical title-case values: `Box`, `Box front`, `Box side`, `Box back`, `Reference`, `Completed`, `In progress`.
  - `PUT /api/v1/image-library/images/{image_id}/content` is admin-only and overwrites the stored image bytes in-place (used by rotate/crop workflows).
  - Overwrite operations preserve the original dedupe hash so future uploads of the original source bytes still clash as duplicates.
  - `POST /api/v1/image-library/images/{image_id}/create-jigsaw` is admin-only and creates a new jigsaw from AI-extracted image metadata.
  - `POST /api/v1/image-library/images/{image_id}/create-jigsaw` only works for unassigned images; assigned images return `409`.
  - Successful create-from-image sets the associated image tag to `Box`.
  - `POST /api/v1/image-library/bulk-create-jigsaws` is admin-only and queues (or runs inline in test mode) one create-from-image action per provided image id.
  - `POST /api/v1/image-library/bulk-create-jigsaws` requires JSON body with `image_ids` as a non-empty list of positive integers (max 500).
  - `POST /api/v1/image-library/bulk-create-jigsaws/unassigned-box` is admin-only and queues create-from-image jobs for all currently unassigned images tagged exactly as `Box`.
  - `GET /api/v1/image-library/bulk-create-jigsaws/{job_id}` returns aggregate job status and counters (`queued` / `running` / `completed` / `failed`).
  - `GET /api/v1/image-library/bulk-create-jigsaws/{job_id}/items` returns per-image outcomes with list pagination.
  - `POST /api/v1/image-embeddings/backfill` is admin-only and queues an image-embedding backfill job across all stored images.
  - `POST /api/v1/image-embeddings/backfill` returns `409` when embedding runtime dependencies are unavailable (for example incompatible `transformers` install).
  - `GET /api/v1/image-embeddings/backfill/{job_id}` is admin-only and returns backfill job status/counters.
  - `GET /api/v1/image-library/images/{image_id}/match-suggestions` requires `image.assign` capability and returns top visual-match jigsaw candidates for one unassigned `Completed` image.
  - `GET /api/v1/image-library/images/{image_id}/match-suggestions` returns `409` when embedding runtime dependencies are unavailable.
  - Each match candidate includes `reference_image` URLs (`content_url`, `thumbnail_url`, `preview_url`) so the admin UI can show side-by-side visual confirmation.
  - Visual-match suggestions require image embeddings to be enabled in server configuration and use cosine similarity against reference-tagged jigsaw images.
  - Embeddings are model-keyed (`model_name@revision`); when model key changes, backfill should be run before relying on suggestions.
  - AI extraction expects these metadata keys: `title`, `series_name`, `series_number`, `manufacturer`/`publisher`, `artist`, `piece_count`, `tags`, `dimensions_cm`, `description`.
  - AI usage is cost-tracked per call (`ai_usage_events`) with token usage and final USD cost.
  - Daily AI spend guardrail: when configured budget is reached, create-from-image requests return `409` and are blocked before provider calls.
  - `POST /api/v1/jigsaws/{id}/enrich-from-images` requires `jigsaw.enrich` capability and uses assigned box-tagged images only (`Box`, `Box front`, `Box side`, `Box back`, and similar `box*` tags) to infer missing metadata.
  - Completed-puzzle images are excluded from enrichment input.
  - Enrichment is non-destructive by default (`overwrite_existing=false`): only empty fields are populated.
  - Enrichment request body optionally accepts `overwrite_existing` (boolean).
  - `GET /api/v1/images/{image_id}/content` returns binary image content for authenticated users, including unassigned library images.
  - `GET /api/v1/images/{image_id}/content` and `GET /api/v1/jigsaws/{id}/images/{image_id}/content` accept optional query param `variant`:
    - `original` (default)
    - `thumbnail`
    - `preview`
  - Bulk uploads write `jigsaw.image_bulk_uploaded` audit events.
  - Image assignment writes `jigsaw.image_assigned` audit events.
  - Image unassignment writes `jigsaw.image_unassigned` audit events.
  - Create-from-image writes `jigsaw.created_from_image` audit events.

- Diary endpoint notes:
  - `GET /api/v1/jigsaws/{id}/diary-entries` requires `diary.read` capability; retired jigsaws return `404` for non-admin callers. Entries are ordered by `completed_at` descending.
  - `GET /api/v1/diary-feed` requires `diary.read` capability and returns a merged, newest-first feed of:
    - formal diary entries (`entry_type = diary_entry`)
    - unassigned completed images (`entry_type = orphan_completed_image`)
  - `GET /api/v1/diary-feed` supports optional query params:
    - `jigsaw_id` (positive integer): returns entries for one jigsaw; orphan rows are excluded in this mode
    - `limit` (integer `1..500`, default `200`)
  - Non-admin callers do not receive feed rows tied to retired jigsaws.
  - `POST /api/v1/jigsaws/{id}/diary-entries` requires authentication and `diary.create` capability. Non-admin callers cannot create entries on retired jigsaws.
    - Created entries persist attribution in `created_by_user_id`.
    - Request body fields are all optional:
    - `completed_at` (UTC ISO 8601 datetime; defaults to current UTC time)
    - `difficulty` (integer 1-5, or empty)
    - `notes` (string up to 4000 characters, no control characters)
  - Creating an entry moves the parent jigsaw's `last_completed_at` forward when the entry is newer.
  - `PATCH /api/v1/diary-entries/{id}` requires authentication and updates one or more of `completed_at`, `difficulty`, `notes`.
    - Administrators can update any entry.
    - Non-admin callers require `diary.update_own` capability and may update only entries where `created_by_user_id` matches the caller.
    - Updates persist attribution in `updated_by_user_id`.
    - At least one of those fields must be included.
    - `completed_at` must be a valid datetime when provided.
  - Updating an entry recomputes the parent jigsaw `last_completed_at` from the latest remaining diary entry timestamp.
  - Tagging an assigned image as `Completed` auto-creates one diary entry (idempotent per image) using the image `captured_at` when available; fallback is current UTC time.
  - Assigning an already-`Completed` image to a jigsaw triggers the same auto-diary behavior.
  - `DELETE /api/v1/diary-entries/{id}` is admin-only and returns the deleted entry; the parent jigsaw's `last_completed_at` is recomputed from remaining entries.
  - Diary entry create/update/delete write audit events (`jigsaw.diary_entry_created`, `jigsaw.diary_entry_updated`, `jigsaw.diary_entry_deleted`).

## HTTP Status Rules

- `200` for successful reads and updates.
- `201` for successful creates.
- `400` for malformed requests.
- `401` for unauthenticated access.
- `403` for unauthorized access.
- `404` for unknown resources.
- `409` for state conflicts.
- `413` for request payloads above the configured server limit.
- `429` for rate-limited requests (for example repeated failed login attempts).
- `422` for validation failures.
- `500` for unhandled server errors.
