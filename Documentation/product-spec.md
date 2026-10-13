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
- Role management with at least `administrator` and `borrower`.
- Jigsaw management:
  - Add (quick-add: title + piece count), edit, archive/retire, restore.
  - Track condition, piece count, and status.
  - Search by title, piece count, availability, and tags.
- Completion diary:
  - Log completions per jigsaw with optional 1-5 difficulty rating and notes.
  - View and delete diary entries.
  - Last-completed date derived from diary entries.
- Image library workflow:
  - Bulk upload one or more images (including zip archives containing image files).
  - Store uploaded images as untagged library assets.
  - Optionally associate uploads to a jigsaw during import.
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
- Admin can log, view, and delete completion diary entries with difficulty ratings and notes per jigsaw.
- Admin can create users and assign one of the supported roles.
- Borrower cannot access admin-only API endpoints.
- All create/update/delete actions write an audit event.
- Core workflows are covered by automated tests.
