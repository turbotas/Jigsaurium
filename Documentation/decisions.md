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

## 2026-06-22 - Migration Safety Guardrail

- Decision: load `.env` in Alembic env and fail fast if the resolved migration target is in-memory SQLite.
- Why: prevents migrations from "succeeding" against `sqlite+pysqlite:///:memory:` while runtime databases remain out of date.
- Decision: run functional/UI tests against Alembic-migrated databases rather than ORM `create_all`.
- Why: reduces drift between test schema behavior and real application environments.

## 2026-06-22 - Relaxed Jigsaw Create Input

- Decision: allow blank values for all jigsaw create inputs in v1, with default `status=available` when omitted/blank.
- Why: supports planned image-driven creation workflows where structured metadata may be populated later.
- Decision: allow duplicate jigsaw titles.
- Why: title uniqueness is not a current domain requirement and cannot be assumed in manual/image-assisted entry.

## 2026-10-13 - Product Pivot to Inventory and Completion Diary

- Decision: shift product focus from lending-library circulation to personal inventory management and a per-jigsaw completion diary.
- Why: owner direction change; the collection catalog and completion history are the core value, lending is a secondary capability.
- Decision: model the diary as timestamped entries per jigsaw (`completed_at`, optional 1-5 `difficulty`, optional `notes`) in a dedicated table rather than fields on the jigsaw record.
- Why: supports repeat completions of the same jigsaw and preserves full history instead of a single latest value.
- Decision: keep existing loan code paths in place but deprioritize all new lending work.
- Why: lending is implemented and tested; removing it would discard working value with no user benefit, and it can be resumed later.
- Decision: streamline jigsaw creation to a quick-add form (title + piece count) with all other metadata editable afterwards.
- Why: reduces record-entry friction; the API already accepts blank values for all jigsaw fields.
- Decision: maintain `jigsaws.last_completed_at` from diary activity (bump forward on entry create, recompute on entry delete) while still allowing manual override via `PATCH /api/v1/jigsaws/{id}`.
- Why: keeps the existing summary field consistent without requiring duplicate date entry.

## 2026-10-13 - Bulk Image Library Intake

- Decision: allow `jigsaw_images.jigsaw_id` to be nullable so images can exist in a standalone library before puzzle association.
- Why: enables fast intake workflows where image ingestion happens before catalog linking.
- Decision: add admin bulk image ingestion endpoint that accepts multi-file uploads and zip archives, importing image entries and skipping non-images.
- Why: dramatically reduces manual effort for initial image library population and supports upcoming image-first creation workflows.
- Decision: keep legacy jigsaw-scoped image endpoints while adding global image library endpoints.
- Why: preserves current admin tooling and tests while incrementally introducing the new workflow.
- Decision: enforce single-jigsaw assignment for images (`jigsaw_id` remains a single nullable FK); allow assignment from unassigned state but block reassignment to a different jigsaw.
- Why: removes ambiguity for downstream image-first creation flows while preserving data integrity and a clear ownership path per image.
- Decision: add SHA-256 image hashing and duplicate suppression for both single-image and bulk/zip upload paths.
- Why: backfill workflows frequently reintroduce the same image under different filenames; byte-level dedupe avoids redundant storage and noisy libraries.
- Decision: image browser transforms (rotate/crop) overwrite image bytes in-place via admin endpoint instead of creating immutable versions.
- Why: current workflow prioritizes speed of cleanup/backfill; full version history can be added later if operational need emerges.
- Decision: preserve the original upload hash during destructive image edits so dedupe continues to clash against source files.
- Why: backfill workflows rely on detecting re-uploads of originals even after derivatives are cropped/rotated in-place.

## 2026-10-13 - AI-Assisted Create-From-Image

- Decision: implement create-from-image as an admin API action that runs AI metadata extraction and maps the JSON result into jigsaw fields.
- Why: image-first intake needs fast structured creation from box imagery where title/piece count/publisher data is often visible.
- Decision: make AI provider integration endpoint/model/key configurable via environment variables using a chat/completions-compatible request contract.
- Why: keeps provider choice flexible while avoiding hardcoded secrets and preserving deploy-time configuration control.
- Decision: persist per-call AI usage/cost telemetry (`ai_usage_events`) including prompt/completion tokens, provider/final cost, and failure details.
- Why: cost accountability and troubleshooting need durable records beyond ephemeral request logs.
- Decision: enforce configurable daily AI spend guardrail (`AI_DAILY_BUDGET_USD`) that blocks new create-from-image calls once reached.
- Why: prevents uncontrolled spend escalation while keeping behavior explicit and auditable.

## 2026-10-14 - Series Metadata and Non-Destructive AI Enrichment

- Decision: store jigsaw series data in dedicated optional fields (`series_name`, `series_number`) instead of embedding it in `title`.
- Why: preserves canonical puzzle titles, avoids fragile string parsing, and supports cleaner filtering/reporting.
- Decision: update AI extraction contract to return `title`, `series_name`, and `series_number` separately.
- Why: box text often mixes branding and title; explicit fields improve downstream normalization and editing.
- Decision: add admin enrich-from-images flow that analyzes all assigned images and fills only empty fields by default.
- Why: back/side images often contain missing metadata (dimensions, artist, publisher), and non-destructive behavior prevents accidental overwrites.

## 2026-10-14 - Capture-Time Backfill and Completed-Image Diary Automation

- Decision: extract and persist image capture time metadata (`captured_at`) from EXIF on upload/import, and treat timezone-less EXIF datetimes as UTC.
- Why: browser-based crop/rotate rewrites may strip EXIF in image bytes; storing capture time in DB preserves diary-relevant metadata.
- Decision: when duplicate image bytes are re-uploaded, skip creating a new image but backfill missing capture metadata on the existing record.
- Why: enables low-risk metadata backfill in dev/prod without content overwrite.
- Decision: automatically create one diary entry per image when an assigned image is tagged `Completed` or a `Completed` image is assigned.
- Why: removes repetitive manual completion logging and ties diary provenance to source images.

## 2026-10-14 - Stored Image Variants for Admin SPA Performance

- Decision: add persisted image derivatives (`thumbnail` and `preview`) to `jigsaw_images` and backfill existing rows via migration.
- Why: admin inventory/image tables now render many thumbnails at once, and repeatedly loading full-resolution originals caused poor perceived performance.
- Decision: serve variants through existing image-content endpoints via `variant` query parameter (`original`/`thumbnail`/`preview`) and include variant URLs in serialized image payloads.
- Why: keeps authz and endpoint surface stable while enabling the SPA to request fit-for-purpose image sizes.

## 2026-10-15 - Non-Blocking Bulk AI Create-From-Image Jobs

- Decision: add persistent bulk AI create job tracking (`bulk_ai_create_jobs` + `bulk_ai_create_job_items`) with status polling endpoints.
- Why: large image batches were causing synchronous UI stalls and long-running request bottlenecks.
- Decision: run bulk jobs asynchronously via an in-process background worker by default, with inline execution in test mode.
- Why: delivers immediate non-blocking UX without adding external queue infrastructure yet, while keeping functional tests deterministic.
