# Domain Rules (v1)

## Role Rules

- `administrator` can manage users, roles, jigsaws, and lending records.
- `borrower` can view catalog availability and own loan records.
- Borrowers cannot mutate user/role data.

## Jigsaw Rules

- Jigsaw create accepts empty values for all user-entered fields in v1 (to support future image-driven creation workflows).
- Optional metadata fields: manufacturer, artist, dimensions (cm), description, and last-completed timestamp.
- Series metadata is supported with optional `series_name` and `series_number` fields, stored separately from `title`.
- When provided, `piece_count` must be a positive integer.
- Duplicate jigsaw titles are allowed.
- Status values in v1:
  - `available`
  - `on_loan`
  - `maintenance`
  - `retired`
- Retired jigsaws are hidden from borrower browse views by default.
- Admins can permanently delete a jigsaw even when it has loan history.
- Permanent delete removes the jigsaw row and hard-deletes its associated images, diary entries, and loans (active or historic).

## Jigsaw Image Rules

- Jigsaw images are stored in the database in v1.
- Each image record includes a tag (for example `Completed`, `Box front`, `Box side`) and binary image content.
- Each image record also stores derived variants (`thumbnail`, `preview`) for faster admin list rendering.
- Image create/list endpoints are administrator-only in the initial rollout.
- A jigsaw image may be unassigned (`jigsaw_id = null`) while it sits in the image library.
- Image library bulk upload accepts one or more image files and/or zip archives containing image files.
- Zip extraction only imports image entries; non-image entries are skipped and reported in the upload response.
- Bulk uploads default all imported images to tag `untagged` unless a tag override is provided.
- Image-library uploads may optionally associate imported images to a jigsaw at upload time.
- Each image can be associated to at most one jigsaw.
- Admin assignment action can attach an unassigned image to a jigsaw; reassigning an already-associated image to a different jigsaw is blocked.
- Admins can permanently delete image-library records (assigned or unassigned) as cleanup actions.
- Every image stores a SHA-256 content hash.
- Duplicate uploads (same bytes, even with different filenames) are ignored using hash matching.
- Images may store `captured_at` extracted from EXIF date metadata; EXIF timestamps without timezone are interpreted as UTC.
- Duplicate uploads can backfill missing `captured_at` metadata on an existing image record without overwriting image content.
- Image browser edits (rotation/crop) overwrite image content in-place but preserve the original dedupe hash.
- Tag/classification updates (`Box`, `Completed`, etc.) are allowed before jigsaw assignment.
- Built-in image-browser tags use canonical title-case values: `Box`, `Box front`, `Box side`, `Box back`, `Completed`, `In progress`.
- Admin create-from-image action can create a new jigsaw from an unassigned image and then bind the image to that created jigsaw.
- Admin enrich-from-images action can infer metadata for an existing jigsaw from assigned box images.
- Enrichment input only uses box-tagged images (for example `Box`, `Box front`, `Box side`, `Box back`); completed-puzzle images are excluded.
- Enrichment is non-destructive by default: only empty fields are populated unless overwrite mode is explicitly requested.
- Create-from-image uses AI metadata extraction and records per-call token/cost usage.
- Create-from-image is blocked when configured daily AI spend budget has been reached.

## Jigsaw Diary Rules

- A diary entry records one completion of a jigsaw: `completed_at` timestamp, optional `difficulty` rating, optional free-text `notes`.
- Multiple diary entries per jigsaw are allowed to support repeat completions.
- `completed_at` defaults to the current UTC time when omitted.
- `difficulty` is an integer from 1 (easy) to 5 (very hard); it may be omitted when unrated.
- `notes` may be up to 4000 characters and must not contain control characters.
- Tagging an assigned image as `Completed`, or assigning an image already tagged `Completed`, auto-creates one diary entry per image.
- Auto-created diary entries use image `captured_at` when available; otherwise they use current UTC time.
- Diary entries are hard-deleted; deleting a jigsaw cascades to its diary entries.
- Diary entry lists are visible to any authenticated user for non-retired jigsaws; create and delete are administrator-only.
- `jigsaws.last_completed_at` is maintained from diary activity:
  - Creating an entry moves it forward when the entry's `completed_at` is newer.
  - Deleting an entry recomputes it to the latest remaining entry's `completed_at`, or clears it when no entries remain.
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
- For administrative checkout workflows, users with `administrator` role are also eligible loan recipients.
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

## Policy Values (deferred for now)

- No max-active-loan limit is enforced in v1.
- No renewal rules are enforced in v1.
- No overdue grace period is enforced in v1.
- Policy caps and renewal behavior can be introduced in a later milestone.
