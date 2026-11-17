# Jigsaurium Product Specification (v1)

## Product Goal

Build a personal jigsaw collection application centered on inventory management and a per-jigsaw completion diary (difficulty ratings and notes), with clear administrative control and auditability. Lending-library circulation features are retained as a secondary capability but are deprioritized for new work.

## User Classes

- Administrator
  - Manage users and roles.
  - Manage jigsaw inventory (create, update, retire, restore).
  - View and manage lending records.
  - View and terminate active application sessions.
  - Trigger, review, download, and delete in-app database backups.
- Member
  - Participate in shared collection workflows (create/update jigsaws, upload/tag/assign images, add diary entries, edit own diary entries).
  - View shared collection and activity according to assigned capabilities.
- Borrower
  - Legacy compatibility role; currently capability-equivalent to `member`.
  - Preserved to avoid breaking existing assignments and STFD mappings during transition.
- Guest (unauthenticated)
  - Browse non-retired jigsaws in the catalog.
  - Browse non-retired jigsaw thumbnails.
  - Sign in.

## Delivery Phases

### Phase 1: Core Inventory and Admin

- User and role management foundation.
- Jigsaw data entity and CRUD screens.
- Inventory statuses and search/filter.
- Audit events for admin changes.
- Activity Log view: readable events (colour-coded), the account's name, a link to the changed record and a "history" link for that record, before/after values for edits, the client IP, and filters by event, account, record type, free-text search and date range.

### Phase 2: Collection Diary (current focus)

- Streamlined quick-add for new jigsaw records (title + piece count).
- Per-jigsaw completion diary entries with 1-5 difficulty rating and notes.
- Completion history views with add/delete.
- Derived last-completed tracking on jigsaw records.

### Phase 3: Borrower and Lending Flow (deprioritized)

- Borrower-facing interface.
- Borrow and return workflows.
- Due dates and overdue status.
- Borrowing history and basic reporting.

Note: lending flows already implemented (admin checkout, loan listing) remain in place; no new lending work is planned until Phases 1-2 are complete.

## Functional Scope (v1)

- Authentication and authorization.
- Public browse access for jigsaw catalog listing (read-only, non-retired records only).
- Public browse access for non-retired jigsaw thumbnails.
- Role management with at least `administrator`, `member`, and legacy `borrower` support during transition.
- Jigsaw management:
  - Add (quick-add: title + piece count), edit, archive/retire, restore.
  - Track condition, piece count, and status.
  - Search by title, piece count, availability, and tags.
  - Open an in-frame jigsaw details panel from jigsaw/image contexts to review one jigsaw's metadata, assigned images, and diary history without leaving current SPA state.
- Completion diary:
  - Log completions per jigsaw with optional 1-5 difficulty rating and notes.
  - View diary entries as any authenticated user.
  - Switch between list and month-calendar diary views.
  - Add diary entries as a normal user.
  - Edit own diary entries as a normal user; administrators can edit any entry.
  - Delete diary entries as an administrator.
  - Surface unlinked `Completed` images alongside formal diary entries in merged completion history views.
  - Suggest visual matches for unlinked `Completed` images and support quick admin assignment.
  - Last-completed date derived from diary entries.
  - Auto-create completion diary entries from `Completed` tagged images when associated to a jigsaw.
- Image library workflow:
  - Bulk upload one or more images (including zip archives containing image files).
  - Store uploaded images as library assets with an initial tag (default `untagged`).
  - Optionally associate uploads to a jigsaw during import.
  - Single-image upload to an existing jigsaw (Collection → Images) picks the jigsaw from a live-search list (title, artist, manufacturer, tags, piece count, with thumbnails), offers only the standard image tags (`untagged`, `Box`, `Box front`, `Box side`, `Box back`, `Reference`, `Completed`, `In progress`), and accepts the image by drag and drop, file chooser, or direct camera capture on mobile, with a preview before upload. The API still accepts other tag values from other clients.
  - Provide a mobile-friendly guided capture flow with six slots: `Box front`, `Box side`, `Box back`, Progress (stored with the `In progress` tag), `Completed`, and `Reference`.
  - For each guided-capture slot, provide both `Choose file from gallery` and `Capture with camera` actions.
  - Require at least one captured image per guided-capture submission.
  - If only Progress and/or `Completed` images are captured, store each as an unassigned image with its own tag (no new jigsaw created).
  - If one or more box/reference images are captured, create a jigsaw, upload all captured images with slot tags, and run enrich-from-images once when at least one box image is present.
  - Guided capture accepts optional title and piece count seed values but does not require them.
  - Guided capture accepts optional free-text comments to capture user feedback/notes alongside uploaded images.
  - Create a new jigsaw from an image via AI metadata extraction (title, series name/number, artist, manufacturer/publisher, piece count, tags, dimensions, description).
  - Enrich an existing jigsaw from associated box images (front/back/side) to populate missing fields.
  - Image browser supports both rectangle crop (two-corner drag) and perspective transform crop (four-corner selection with draggable corner adjustment before apply).
  - Track AI token/cost usage per create-from-image call and enforce daily spend guardrails.
- Lending management (deprioritized, existing capability retained):
  - Create loan.
  - Return loan.
  - Mark overdue.
- API-first backend for SPA frontend.

## Non-Goals (v1)

- Payments and fine processing.
- Native mobile app.
- Recommendation engine.
- Multi-branch synchronization.

## SPA + API Expectations

- Frontend is a single-page app that consumes backend APIs.
- Backend provides versioned JSON APIs.
- Authorization enforced at API layer, not only UI.
- Frontend keeps presentation concerns; backend owns business rules and data integrity.

## Acceptance Criteria (initial)

- Admin can create, edit, retire, and restore jigsaw records via UI.
- Admin can quick-add a jigsaw with only title and piece count, then enrich it later via edit.
- Admin can create a jigsaw from an unassigned image using AI-assisted metadata extraction.
- Admin can run non-destructive AI enrichment on an existing jigsaw using its assigned images.
- Admin can submit a mobile guided-capture upload with at least one slot populated.
- Guided capture with only Progress and/or Completed images stores them unassigned (`In progress` / `Completed`) without creating a jigsaw.
- Guided capture that includes a box or reference image creates a jigsaw and tags/uploads captured slot images; enrich-from-images runs once when box imagery is included.
- Authenticated non-admin users can log and edit their own completion diary entries.
- Admin can log, edit, and delete completion diary entries with difficulty ratings and notes per jigsaw.
- Diary tab supports list and month-calendar modes, with month navigation in calendar mode.
- Admin can create users and assign one of the supported roles.
- Admin can deactivate/reactivate users, and can permanently delete only inactive users that do not have an active app session.
- Borrower cannot access admin-only API endpoints.
- Unauthenticated users can browse non-retired jigsaws and cannot access authenticated-only features.
- All create/update/delete actions write an audit event.
- Core workflows are covered by automated tests.
