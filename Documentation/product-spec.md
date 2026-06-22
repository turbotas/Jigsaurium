# Jigsaurium Product Specification (v1)

## Product Goal

Build a lending-library application for jigsaw inventory and circulation, with clear administrative control, borrower access, and auditability.

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

### Phase 2: Borrower and Lending Flow

- Borrower-facing interface.
- Borrow and return workflows.
- Due dates and overdue status.
- Borrowing history and basic reporting.

## Functional Scope (v1)

- Authentication and authorization.
- Role management with at least `administrator` and `borrower`.
- Jigsaw management:
  - Add, edit, archive/retire, restore.
  - Track condition, piece count, and status.
  - Search by title, piece count, availability, and tags.
- Lending management:
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
- Admin can create users and assign one of the supported roles.
- Borrower cannot access admin-only API endpoints.
- All create/update/delete actions write an audit event.
- Core workflows are covered by automated tests.
