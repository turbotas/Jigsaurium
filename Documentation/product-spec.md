# Jigsaurium Product Specification (v1)

## Product Goal

Build a personal jigsaw collection application centered on inventory management and a per-jigsaw completion diary (difficulty ratings and notes), with clear administrative control and auditability. Lending-library circulation features are retained as a secondary capability but are deprioritized for new work.

## User Classes

- Administrator
  - Manage users and roles.
  - Manage jigsaw inventory (create, update, retire, restore).
  - View and manage lending records.
- Borrower
  - View available jigsaws.
  - View own borrowing status and history.
  - Borrow and return jigsaws (subject to policy and implementation phase).
- Guest (unauthenticated)
  - Browse non-retired jigsaws in the catalog.
  - Sign in.

## Delivery Phases

### Phase 1: Core Inventory and Admin

- User and role management foundation.
- Jigsaw data entity and CRUD screens.
- Inventory statuses and search/filter.
- Audit events for admin changes.

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
- Role management with at least `administrator`, `member`, and legacy `borrower` support during transition.
- Jigsaw management:
  - Add (quick-add: title + piece count), edit, archive/retire, restore.
  - Track condition, piece count, and status.
  - Search by title, piece count, availability, and tags.
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
  - Provide a mobile-friendly guided capture flow with slots for `Box front`, `Box side`, `Box back`, and `Completed` images.
  - Require at least one captured image per guided-capture submission.
  - If only `Completed` is captured, store it as an unassigned `Completed` image (no new jigsaw created).
  - If one or more box images are captured, create a jigsaw, upload all captured images with slot tags, and run enrich-from-images once for that jigsaw.
  - Guided capture accepts optional title and piece count seed values but does not require them.
  - Guided capture accepts optional free-text comments to capture user feedback/notes alongside uploaded images.
  - Create a new jigsaw from an image via AI metadata extraction (title, series name/number, artist, manufacturer/publisher, piece count, tags, dimensions, description).
  - Enrich an existing jigsaw from associated box images (front/back/side) to populate missing fields.
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
- Completed-only guided capture stores an unassigned `Completed` image without creating a jigsaw.
- Guided capture that includes a box image creates a jigsaw, tags/uploads captured slot images, and runs enrich-from-images once.
- Authenticated non-admin users can log and edit their own completion diary entries.
- Admin can log, edit, and delete completion diary entries with difficulty ratings and notes per jigsaw.
- Diary tab supports list and month-calendar modes, with month navigation in calendar mode.
- Admin can create users and assign one of the supported roles.
- Borrower cannot access admin-only API endpoints.
- Unauthenticated users can browse non-retired jigsaws and cannot access authenticated-only features.
- All create/update/delete actions write an audit event.
- Core workflows are covered by automated tests.
