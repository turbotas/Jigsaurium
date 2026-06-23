## Documentation Index

This folder defines the product, architecture, and delivery rules for Jigsaurium.

- `product-spec.md`: Product goals, roles, scope, workflows, and acceptance criteria.
- `architecture.md`: SPA/API architecture, backend boundaries, data model, and runtime targets.
- `design-system.md`: GOV.UK Design System integration and customization rules.
- `api-contract.md`: API conventions, payload shape, pagination, and error format.
- `domain-rules.md`: Business rules for roles, jigsaw lifecycle, and loan lifecycle.
- `operations-and-security.md`: runtime config, proxy trust model, logging, and release checks.
- `roadmap.md`: Phase-based delivery plan for multiple developers.
- `decisions.md`: ADR-style decision log.

## Working Agreement

- Update docs before coding major features.
- Any schema change must include an Alembic revision and downgrade.
- Do not edit GOV.UK vendor assets directly; apply branding in app overrides only.
- Keep role and permission changes aligned with `product-spec.md` and `architecture.md`.

## Current Implementation Snapshot (2026-06-22)

- Admin SPA authentication is live (`/api/v1/auth/login`, `/api/v1/auth/me`, `/api/v1/auth/logout`) with CSRF enforcement.
- User management is live with multi-role assignment (`administrator` and `borrower` can be combined).
- Jigsaw inventory CRUD is live, with relaxed create input for image-assisted workflows (all create fields may be blank).
- Loan checkout is live for administrators (`POST /api/v1/loans`) with default 28-day due date.
- Jigsaw image upload/list/content endpoints are live (`/api/v1/jigsaws/{id}/images...`) with DB-backed storage.
- Test suite is migration-driven for functional/UI flows to reduce schema drift between CI/test and runtime DBs.

## Pull Request Checklist

- Spec and acceptance criteria are updated for the feature.
- API contract changes are documented.
- Migration added (if schema changed) and `alembic upgrade head` succeeds.
- Role/permission impacts are documented and tested.
- GOV.UK component conventions are followed.

## Delivery Automation Notes

- CI workflows are defined in `.github/workflows/`.
- `API and Core Tests` runs on pushes and pull requests.
- `UI Smoke Tests` runs on pull requests and pushes to `main` and `master`.
- Developer operational scripts are documented in `README.md`, including:
  - test execution (`scripts/run_tests.bat`, `scripts/run_tests.sh`)
  - dependency checks (`scripts/check_updates.bat`, `scripts/check_updates.sh`)
  - GOV.UK asset updates (`scripts/update_govuk_assets.bat`, `scripts/update_govuk_assets.sh`)
  - admin bootstrap (`scripts/bootstrap_admin.py`)

## Pending Decisions Checklist

- Confirm SPA framework choice (React, Vue, Svelte, or other).
- Confirm trusted proxy policy model (CIDR allowlist and/or fixed proxy depth).
- Confirm borrowing policy caps (renewal rules, max active loans) when borrower self-service lending is introduced.

## Suggested Next Work

- Add administrative loan return workflow and borrower-safe return outcome handling.
- Add borrower-facing loan/history views for Milestone 2.
- Add pagination and filtering for loan/image lists once record counts grow.
- Add object-storage option (S3-compatible) for images when volume/performance requirements increase.
