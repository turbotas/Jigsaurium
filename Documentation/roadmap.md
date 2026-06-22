# Delivery Roadmap

## Milestone 0: Foundations

- Finalize product and architecture specs.
- Finalize API contract, domain rules, and operations/security specs.
- Set dependency baseline (Flask, SQLAlchemy, Alembic, PyMySQL).
- Establish DB connection and migration scaffolding.

## Milestone 1: Admin + Jigsaw Management

- Implement authentication and role model.
- Implement user management APIs and admin screens.
- Implement jigsaw CRUD APIs and SPA views.
- Add audit events for administrative mutations.

## Milestone 2: Borrower + Lending

- Implement borrower-facing jigsaw browsing.
- Implement loan creation and return workflows.
- Add due-date and overdue status handling.
- Add borrower history views.

## Milestone 3: Hardening and Deploy Readiness

- Add API and workflow integration tests.
- Add Docker packaging and runtime documentation.
- Add Kubernetes deployment shape documentation and base manifests.
- Define release/update runbooks (full automation later).

## Team Lanes

- Lane A: user/role management and authz.
- Lane B: jigsaw CRUD and inventory states.
- Lane C: loan lifecycle and borrower UI.
- Shared: migrations, API standards, documentation, test coverage.
