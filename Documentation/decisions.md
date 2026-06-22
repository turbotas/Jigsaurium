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
