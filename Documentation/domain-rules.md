# Domain Rules (v1)

## Role Rules

- `administrator` can manage users, roles, lending records, AI operations, and destructive lifecycle actions.
- `member` can use shared household collection workflows: jigsaw create/read/update/enrich, diary create/read/update-own, image upload/library/tag/assign, and audit read.
- `borrower` remains supported as a legacy compatibility role and currently maps to member-style capabilities.
- Borrowers cannot mutate user/role data.

## Identity Rules

- STFD UNI (`sub`) is persisted in `users.auth_subject` and is the primary identity link for JIT sign-in.
- STFD role UNI values are mapped to local role rows via `roles.uni`.
- In STFD mode, successful sign-in performs JIT user provisioning/sync and refreshes local role assignments from token role UNI claims.
- In STFD mode, profile/password edits are managed externally and `PATCH /api/v1/auth/me` is disabled.

## Jigsaw Rules

- Jigsaw create accepts empty values for all user-entered fields in v1 (to support future image-driven creation workflows).
- Optional metadata fields: manufacturer, artist, dimensions (cm), description, and last-completed timestamp.
- Series metadata is supported with optional `series_name` and `series_number` fields, stored separately from `title`.
- When provided, `piece_count` must be a positive integer.
- Duplicate jigsaw titles are allowed.
- Jigsaw metadata edits require capability `jigsaw.update`.
- Non-admin callers cannot retire jigsaws via metadata edits (setting status to `retired` is forbidden).
- Status values in v1:
  - `available`
  - `on_loan`
  - `maintenance`
  - `retired`
- Retired jigsaws are hidden from non-admin browse views by default, including unauthenticated catalog browse.
- Admins can permanently delete a jigsaw even when it has loan history.
- Permanent delete removes the jigsaw row and hard-deletes its associated images, diary entries, and loans (active or historic).

## Jigsaw Image Rules

- Jigsaw images are stored in the database in v1.
- Each image record includes a tag (for example `Completed`, `Box front`, `Box side`) and binary image content.
- Each image record also stores derived variants (`thumbnail`, `preview`) for faster admin list rendering.
- Jigsaw image list requires `image.manage_library`; jigsaw image upload requires `image.upload`.
- A jigsaw image may be unassigned (`jigsaw_id = null`) while it sits in the image library.
- Image library bulk upload accepts one or more image files and/or zip archives containing image files.
- Zip extraction only imports image entries; non-image entries are skipped and reported in the upload response.
- Bulk uploads default all imported images to tag `untagged` unless a tag override is provided.
- Image-library uploads may optionally associate imported images to a jigsaw at upload time.
- Each image can be associated to at most one jigsaw.
- Callers with `image.assign` can attach an unassigned image to a jigsaw and can unassign by setting `jigsaw_id = null`; reassigning an already-associated image to a different jigsaw is blocked.
- Visual match suggestions for unassigned `Completed` images require capability `image.assign`.
- Admins can permanently delete image-library records (assigned or unassigned) as cleanup actions.
- Non-admin callers with `image.delete` can permanently delete only unassigned image-library records.
- Every image stores a SHA-256 content hash.
- Duplicate uploads (same bytes, even with different filenames) are ignored using hash matching.
- Images may store `captured_at` extracted from EXIF date metadata; EXIF timestamps without timezone are interpreted as UTC.
- Images may store optional user-entered feedback/notes (`user_comment`) from upload workflows.
- Duplicate uploads can backfill missing `captured_at` metadata on an existing image record without overwriting image content.
- Image browser edits (rotation/crop) overwrite image content in-place but preserve the original dedupe hash.
- Overwrite image-content edits in the image browser require capability `image.upload`.
- Tag/classification updates (`Box`, `Completed`, etc.) are allowed before jigsaw assignment.
- Built-in image-browser tags use canonical title-case values: `Box`, `Box front`, `Box side`, `Box back`, `Completed`, `In progress`.
- Admin create-from-image action can create a new jigsaw from an unassigned image and then bind the image to that created jigsaw.
- Callers with `jigsaw.enrich` can infer metadata for an existing jigsaw from assigned box images.
- Enrichment input only uses box-tagged images (for example `Box`, `Box front`, `Box side`, `Box back`); completed-puzzle images are excluded.
- Enrichment is non-destructive by default: only empty fields are populated unless overwrite mode is explicitly requested.
- Create-from-image uses AI metadata extraction and records per-call token/cost usage.
- Create-from-image is blocked when configured daily AI spend budget has been reached.

## Jigsaw Diary Rules

- A diary entry records one completion of a jigsaw: `completed_at` timestamp, optional `difficulty` rating, optional free-text `notes`.
- Multiple diary entries per jigsaw are allowed to support repeat completions.
- Diary entries store attribution fields: `created_by_user_id` (required) and `updated_by_user_id` (optional).
- `completed_at` defaults to the current UTC time when omitted.
- `difficulty` is an integer from 1 (easy) to 5 (very hard); it may be omitted when unrated.
- `notes` may be up to 4000 characters and must not contain control characters.
- Tagging an assigned image as `Completed`, or assigning an image already tagged `Completed`, auto-creates one diary entry per image.
- Auto-created diary entries use image `captured_at` when available; otherwise they use current UTC time.
- Diary entries are hard-deleted; deleting a jigsaw cascades to its diary entries.
- Diary entry lists are visible to any authenticated user for non-retired jigsaws.
- Diary create requires authenticated caller capability `diary.create`.
- Diary update requires authenticated caller capability:
  - `diary.update_any` for any entry (administrator behavior)
  - `diary.update_own` for entries where `created_by_user_id` matches the caller
- Diary delete remains administrator-only in v1.
- A merged completion feed is available to authenticated users and includes both formal diary entries and unassigned `Completed` images.
- In merged-feed views, unassigned completed images are represented as orphan completion rows until linked to a jigsaw.
- `jigsaws.last_completed_at` is maintained from diary activity:
  - Creating an entry moves it forward when the entry's `completed_at` is newer.
  - Updating or deleting an entry recomputes it to the latest remaining entry's `completed_at`, or clears it when no entries remain.
  - Manual override via jigsaw update remains possible but may be overwritten by later diary activity.

## Jigsaw State Transitions

- `available` -> `on_loan` when checked out.
- `on_loan` -> `available` when returned in good condition.
- `on_loan` -> `maintenance` when returned damaged/incomplete.
- `available` or `maintenance` -> `retired` by admin action.
- `retired` -> `available` by admin restore action.

## Loan Rules

- A jigsaw can have only one active loan at a time.
- A borrower can hold multiple active loans in v1 (no policy cap enforced yet).
- Loan recipient eligibility includes active users with role `member`, `borrower` (legacy), or `administrator`.
- Loan states in v1:
  - `active`
  - `returned`
  - `overdue`
- Overdue is derived from due date and return status.
- New loans set `due_at` to four weeks (28 days) after `checked_out_at`.
- Returning a loan sets `returned_at` and transitions status to `returned`.

## Audit Rules

- Record audit events for create/update/delete and state transition actions.
- Each event includes actor, action, entity type/id, timestamp, and request context.
- Request context includes resolved client address details from trusted forwarded headers.
- Audit read visibility is capability-based: administrators can read all events; non-admin callers with `audit.read` can read events where they are the actor.

## Policy Values (deferred for now)

- No max-active-loan limit is enforced in v1.
- No renewal rules are enforced in v1.
- No overdue grace period is enforced in v1.
- Policy caps and renewal behavior can be introduced in a later milestone.
