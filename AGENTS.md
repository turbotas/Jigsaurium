# AI Collaboration Guide

This repository is maintained by human developers and AI coding agents.

## Start Here

Before making changes, read:

1. `Documentation/README.md`
2. `Documentation/product-spec.md`
3. `Documentation/architecture.md`
4. `Documentation/api-contract.md`
5. `Documentation/domain-rules.md`
6. `Documentation/operations-and-security.md`
7. `Documentation/design-system.md`
8. `Documentation/decisions.md`

## Project Defaults

- Backend: Flask
- ORM: SQLAlchemy 2.x
- Migrations: Alembic CLI (direct)
- Database: MariaDB via `DATABASE_URL`
- Frontend: SPA + JSON API (`/api/v1`)
- Design System: GOV.UK (light branding only)

## Rules for AI Contributors

- Follow documented specs; do not invent conflicting behavior.
- If code changes require spec changes, update docs in the same change.
- Do not edit GOV.UK vendor source directly.
- Keep custom UI styling in project override layers.
- Enforce role checks in backend APIs, not only in the UI.
- Add migrations for every schema change, including downgrade paths.
- Preserve audit logging for administrative data mutations.
- Respect proxy/header policy (RFC7239 `Forwarded` + trusted fallback headers).

## API and Domain Guardrails

- Use versioned endpoints under `/api/v1`.
- Keep response/error payloads aligned with `Documentation/api-contract.md`.
- Keep jigsaw and loan state transitions aligned with `Documentation/domain-rules.md`.
- Do not broaden permissions for `borrower` without updating specs.

## Security and Ops Guardrails

- Do not hardcode secrets.
- Use environment variables for runtime configuration.
- Keep structured logging fields consistent with `Documentation/operations-and-security.md`.
- Assume reverse-proxy deployment in all environments.

## Workflow Expectations

- Make small, reviewable changes.
- Add or update tests for behavior changes.
- Keep naming clear and consistent with existing code.
- Record major architectural changes in `Documentation/decisions.md`.

## If Requirements Are Unclear

- Prefer existing documentation over assumptions.
- If still ambiguous, add a short note in the relevant documentation file under a "Pending Decisions" section.
