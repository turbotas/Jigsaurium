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

## Milestone 2: Borrower + Lending

- [~] Implement borrower-facing jigsaw browsing.
- [~] Implement loan creation workflow (admin-first).
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
- Lane B: jigsaw CRUD and inventory states.
- Lane C: loan lifecycle and borrower UI.
- Shared: migrations, API standards, documentation, test coverage.

## Immediate Next Slice

- Add `POST /api/v1/loans/{id}/return` with audit events and jigsaw status transition rules.
- Add borrower-facing list endpoints/views for own active and historical loans.
- Add pagination for `jigsaws`, `loans`, and `jigsaw_images` list views.
