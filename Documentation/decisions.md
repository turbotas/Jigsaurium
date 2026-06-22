# Architecture Decision Log

## 2026-06-21 - ORM and Migrations

- Decision: Use SQLAlchemy 2.x with direct Alembic CLI.
- Why: explicit migration control and clear multi-developer workflow.

## 2026-06-21 - Database

- Decision: Use MariaDB from day one.
- Why: aligns with existing database service and production direction.

## 2026-06-21 - Connection Standard

- Decision: Use `DATABASE_URL` as the DB connection env var.
- Why: cross-tool convention and easy runtime portability.

## 2026-06-21 - Design System

- Decision: Use GOV.UK Design System as base, with light branding.
- Why: consistent, accessible patterns with strong existing guidance.

## 2026-06-21 - Runtime Targets

- Decision: Support native Windows, native Linux, Docker, and Kubernetes-ready deployments.
- Why: required by operating environment strategy.

## 2026-06-21 - Proxy and Header Strategy

- Decision: Treat all environments as reverse-proxy deployments and process RFC7239 `Forwarded` headers for logging/audit context.
- Why: runtime traffic is proxy-terminated in dev, test, and production.
- Decision: accept `X-Forwarded-*` headers as fallbacks when needed.
- Why: interoperability with existing proxy stacks and ingress defaults.

## 2026-06-22 - GOV.UK Asset Vendoring and Update Workflow

- Decision: Pin `govuk-frontend` in `package.json` and vendor runtime assets into `app/static/vendor/govuk`.
- Why: stable, reproducible frontend assets with no CDN dependency at runtime.
- Decision: Keep custom styles in `app/static/css/styles.css` and never modify vendored GOV.UK files directly.
- Why: preserves clean upgrade boundaries and aligns with design-system policy.
- Decision: Add dev startup warning when vendored GOV.UK version is behind npm latest.
- Why: makes dependency drift visible during normal development flow.

## 2026-06-22 - SPA Authentication Approach

- Decision: Use secure cookie session authentication for the SPA/API flow.
- Why: aligns with Flask runtime defaults and keeps server-side authorization context simple for Milestone 1.
- Decision: Expose `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, and `POST /api/v1/auth/logout` as the initial auth endpoints.
- Why: provides explicit login state bootstrap, identity check, and session teardown.
- Decision: Require `X-CSRF-Token` on authenticated mutating endpoints.
- Why: enforces CSRF protection for cookie-based API calls as required by operations/security rules.
- Decision: Require password verification on login and store only password hashes in the `users` table.
- Why: avoids passwordless impersonation by email and keeps credential storage aligned with basic security expectations.
- Decision: Bootstrap the first admin account through a local script (`scripts/bootstrap_admin.py`) with secure password prompt.
- Why: keeps first-credential setup out of public endpoints and avoids hardcoded bootstrap secrets.

## 2026-06-22 - Initial Lending Policy Scope

- Decision: implement administrative loan checkout first via the existing admin SPA.
- Why: delivers core circulation capability with minimal UI/API surface before borrower self-service flows.
- Decision: set default `due_at` to four weeks (28 days) from checkout time.
- Why: provides consistent due-date behavior without adding configurable policy controls yet.
- Decision: defer max active loan caps, renewal limits, and grace-period enforcement.
- Why: project direction is intentionally low-friction for initial rollout; policy controls can be layered in later.

## 2026-06-22 - Jigsaw Metadata and Image Storage

- Decision: extend jigsaw records with manufacturer, dimensions in cm, artist, description, and last-completed timestamp.
- Why: operational catalog data needs richer descriptive fields for stock management.
- Decision: store jigsaw image binaries in the application database for v1.
- Why: projected media volume is modest and database-backed storage keeps backups and portability simple in early phases.
