# Delivery Roadmap

## Status Legend

- [x] complete
- [~] in progress
- [ ] not started

## Milestone 0: Foundations

- [x] Finalize product and architecture specs.
- [x] Finalize API contract, domain rules, and operations/security specs.
- [x] Set dependency baseline (Flask, SQLAlchemy, Alembic, PyMySQL).
- [x] Establish DB connection and migration scaffolding.

## Milestone 1: Admin + Jigsaw Management

- [x] Implement authentication and role model.
- [x] Implement user management APIs and admin screens.
- [x] Implement jigsaw CRUD APIs and SPA views.
- [x] Add audit events for administrative mutations.
- [x] Extend jigsaw metadata fields and DB-backed image uploads.

## Milestone 2: Inventory + Completion Diary (current focus)

- [x] Streamline jigsaw quick-add (title + piece count; full metadata via edit).
- [x] Add completion diary entries per jigsaw (completed_at, 1-5 difficulty, notes).
- [x] Maintain `last_completed_at` from diary entries.
- [x] Add image-library bulk upload (multi-file + zip extraction, optional jigsaw association).
- [x] Add image-library assignment action (attach unassigned image to one existing jigsaw).
- [x] Add create-from-image workflow (AI metadata extraction + jigsaw creation + image binding).
- [ ] Add diary entry edit (PATCH) support.
- [ ] Add pagination for `jigsaws`, `loans`, `jigsaw_images`, and `diary_entries` list views.
- [ ] Add collection-level diary/stats views (for example recent completions, difficulty breakdown).

## Milestone 2b: Borrower + Lending (deprioritized; existing code retained)

- [~] Implement borrower-facing jigsaw browsing.
- [x] Implement loan creation workflow (admin-first).
- [ ] Implement loan return workflow.
- [~] Add due-date handling (default 28-day checkout due date).
- [ ] Add borrower history views.

## Milestone 3: Hardening and Deploy Readiness

- [~] Add API and workflow integration tests.
- [ ] Add Docker packaging and runtime documentation.
- [ ] Add Kubernetes deployment shape documentation and base manifests.
- [ ] Define release/update runbooks (full automation later).

## Team Lanes

- Lane A: user/role management and authz.
- Lane B: jigsaw CRUD, inventory states, and completion diary.
- Lane C: loan lifecycle and borrower UI (paused).
- Shared: migrations, API standards, documentation, test coverage.

## Immediate Next Slice

- Add `PATCH /api/v1/diary-entries/{id}` for editing notes/difficulty/completed_at.
- Add pagination for `jigsaws`, `loans`, and `jigsaw_images` list views.
- When lending resumes: add `POST /api/v1/loans/{id}/return` with audit events and jigsaw status transition rules, plus borrower-facing own-loan views.
