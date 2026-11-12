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

## 2026-10-16 - CLIP Embedding Backfill and Visual Match Suggestions

- Decision: introduce per-image embedding storage keyed by `model_name@revision` and generate vectors for all image-library rows.
- Why: visual matching between historical completed photos and jigsaw references must remain model-consistent and resilient to tag/workflow changes.
- Decision: add admin-triggered asynchronous embedding backfill jobs with status polling.
- Why: initial rollout requires historical backfill without blocking request threads, and model upgrades require controlled recomputation.
- Decision: use visual-match suggestions for unassigned `Completed` images by scoring cosine similarity against reference-tagged jigsaw images.
- Why: historical data lacks reliable filename/time proximity signals, so visual similarity is the primary reconciliation mechanism.

## 2026-10-17 - Mobile Guided Capture Workflow

- Decision: add a mobile-first guided capture interface with four photo slots (`Box front`, `Box side`, `Box back`, `Completed`) and optional title/piece-count seed fields.
- Why: smartphone capture is now the fastest intake path for new jigsaws and should avoid desktop-first multi-step upload friction.
- Decision: require at least one slot image, and branch workflow by slot mix.
- Why: supports both cataloging new boxes and diary-only completed-photo uploads in one entry point.
- Decision: when only `Completed` is provided, store as unassigned `Completed` image and do not create a jigsaw.
- Why: a standalone completed photo often lacks enough metadata to safely identify a jigsaw at capture time.
- Decision: when any box slot is present, create a jigsaw, upload/tag all captured slot images, then run one non-destructive enrich-from-images call.
- Why: this reuses proven APIs while giving users a single, responsive workflow that extracts metadata from all box photos together.

## 2026-10-17 - Upload Comments for User Feedback

- Decision: add optional per-upload `comment` support and persist it as `jigsaw_images.user_comment`.
- Why: mobile capture and image-import workflows need a simple place for user feedback/notes at upload time.
- Decision: when a completed image auto-creates a diary entry, prefer the image `user_comment` as the diary `notes` value.
- Why: user-entered completion context should flow directly into the diary without extra edit steps.

## 2026-10-19 - Dependency Update Promotion Workflow

- Decision: keep version ranges in `requirements/base.txt` and `requirements/dev.txt`, and store tested exact installs in `requirements/known-good-dev.txt` and `requirements/known-good-prod.txt`.
- Why: range files preserve upgrade intent while known-good locks preserve reproducibility and rollback clarity.
- Decision: promote Python updates through `scripts/update_python_dependencies.(bat|sh)` in full-profile mode by default (upgrade resolvable packages, run pytest for dev profile, then sync direct requirement lower bounds and refresh known-good lock).
- Why: a small-team workflow needs one-command batch promotion with a single test gate rather than per-package manual selection.

## 2026-10-19 - Shared-Household Attribution and Diary Capability Relaxation

- Decision: keep jigsaw, image, and diary data globally visible/editable within household scope (no per-user collection ownership model yet).
- Why: the current deployment is family/household based and intentionally shares one collection namespace.
- Decision: add attribution fields to diary/image records (`jigsaw_diary_entries.created_by_user_id`, `jigsaw_diary_entries.updated_by_user_id`, `jigsaw_images.uploaded_by_user_id`).
- Why: shared scope still needs accountability for user-contributed edits and uploads.
- Decision: allow non-admin authenticated users to create diary entries and update only entries they created.
- Why: diary contribution is core user functionality; limiting updates to self-authored entries keeps low-friction collaboration with basic guardrails.
- Decision: include derived `capabilities` in auth payloads for SPA feature-gating.
- Why: capability-driven UI/API evolution is less brittle than hardcoded role-name checks and supports future role changes.
- Decision: seed a `member` role while retaining `borrower` as legacy compatibility.
- Why: normal-user diary capability should be represented by a role name aligned to shared-household usage without breaking existing borrower assignments.

## 2026-10-19 - Application-Layer 404 Streak Ban

- Decision: add an application-layer request shield that temporarily blocks a client IP for 24 hours after 5 consecutive `404` responses.
- Why: production runs behind an appliance proxy with limited configurability, so scanner suppression must be enforced in Flask rather than at the proxy edge.
- Decision: key ban and login-throttle identity on resolved client IP from trusted proxy headers (`Forwarded` preferred, `X-Forwarded-For` fallback) and ignore forwarded headers from untrusted peers.
- Why: request socket addresses reflect local proxy hops in deployment; security controls must use the original caller address while resisting header spoofing.
- Decision: persist blocked-IP entries in a dedicated `blocked_ips` table and expose administrator endpoints/UI for manual add/remove and visibility.
- Why: operators need durable state and manual remediation controls that survive app restarts and support appliance-proxy environments.

## 2026-10-21 - STFD-Backed JIT Authentication and UNI Mapping

- Decision: integrate authentication with STFD JWT assertions using JIT user provisioning/synchronization on each successful login.
- Why: STFD is the cross-environment identity provider; JIT avoids manual pre-provisioning and keeps local identity data current.
- Decision: treat `users.auth_subject` as the canonical external identity key (STFD user UNI) and add role-level UNI mapping via `roles.uni`.
- Why: token `sub` and role UNI claims must map deterministically into local authorization state.
- Decision: emit explicit audit events for `user.provisioned_from_stfd`, `user.synced_from_stfd`, and `auth.login`.
- Why: operators need a clear trail for first-seen identities, subsequent UNI-linked profile updates, and access events.

## 2026-10-21 - SemVer Releases, Environment Pointers, and Runtime Build Metadata

- Decision: use immutable SemVer release tags (`vMAJOR.MINOR.PATCH`) for container releases.
- Why: immutable tags provide reproducible deployments, clear rollback points, and auditable release history.
- Decision: use mutable pointer tags (`dev`, `test`, `prod`) that are promoted to reference a release image without rebuilding.
- Why: promotion by pointer simplifies staged rollout while preserving release immutability.
- Decision: surface runtime build metadata (`APP_ENV`, `APP_VERSION`, `APP_BUILD_SHA`, `APP_BUILD_TIME`) in the UI footer and API health response.
- Why: operators need immediate visibility of deployed environment and version/build identity for diagnostics and change verification.

## 2026-10-24 - Public Catalog Browse for Unauthenticated Users

- Decision: allow unauthenticated users to call `GET /api/v1/jigsaws` and `GET /api/v1/jigsaws/thumbnail-images`.
- Why: visitors need read-only browse access to the collection before signing in.
- Decision: keep all non-browse features authenticated and capability-guarded, and continue filtering retired jigsaws for non-admin/unauthenticated callers.
- Why: this preserves least-privilege defaults while exposing a safe guest catalog surface.

## 2026-10-25 - Deterministic Embedding Runtime with Startup Warm Load

- Decision: pin embedding model revision to a specific commit and support vendored local-path loading (`IMAGE_EMBEDDING_MODEL_LOCAL_PATH`) with local-only mode enabled by default.
- Why: deterministic performance and behavior require eliminating runtime drift and preventing implicit Hub fetches.
- Decision: warm-load the embedding model at app startup when embeddings are enabled, with configurable fail-fast behavior on startup errors.
- Why: first embedding request previously absorbed model load latency and could time out; startup warm-load moves that cost out of user request paths.
- Decision: add admin diagnostics API/UI for embeddings health and performance (`GET /api/v1/image-embeddings/diagnostics`).
- Why: operators need visibility into stale/missing embeddings and observed per-image compute timings to manage backfills and runtime readiness.

## 2026-11-03 - Admin Session Registry and Termination Controls

- Decision: add a server-side `user_sessions` registry and require authenticated app requests to map to an active session row.
- Why: administrators need visibility/control over active app sessions, and API-level enforcement must support forced sign-out.
- Decision: add admin-only endpoints and UI for active-session listing and per-session termination (`GET /api/v1/security/sessions`, `DELETE /api/v1/security/sessions/{id}`).
- Why: operations need direct remediation for suspicious or stale sessions without waiting for user action.
- Decision: enforce inactivity expiry at 120 minutes by default (configurable via `SESSION_IDLE_TIMEOUT_MINUTES`) and record session origin using resolved client IP from trusted forwarded headers.
- Why: this aligns with low-sensitivity app posture while preserving accurate client attribution behind reverse proxies.

## 2026-11-03 - Capability Catalogue Documentation Before Runtime Role-Capability Editing

- Decision: defer runtime role-capability management UI/API (issue #8 scope) and first publish a canonical role capability catalogue in documentation.
- Why: current capability mapping is static and operationally stable; documenting defaults addresses immediate support/troubleshooting needs with lower delivery risk.
- Decision: explicitly include public unauthenticated browse scope in authorization documentation (`GET /api/v1/jigsaws`, `GET /api/v1/jigsaws/thumbnail-images`, and constrained non-retired preview/thumbnail image access).
- Why: the security posture now intentionally includes guest read-only data access and must be clearly documented alongside role capabilities.

## 2026-11-03 - In-App MySQL-Compatible Database Backups

- Decision: add administrator-only in-app backup management endpoints and UI for creating, listing, and downloading database backups.
- Why: operators need a built-in backup path that does not depend on external tools for routine exports.
- Decision: emit backups as MySQL-compatible SQL (`mysql_sql`) even when runtime DB engine differs (for example SQLite dev environments).
- Why: restore/import portability into MySQL tooling (including phpMyAdmin) is required across environments.
- Decision: export binary/blob fields using `UNHEX(...)` SQL literals with chunked variable assembly for large blobs.
- Why: image-heavy rows can exceed practical packet sizes if emitted as single oversized statements; chunked assembly reduces packet-size risk during import.
- Decision: store backup files compressed by default (`gzip`), with optional `bzip2` or uncompressed output via configuration.
- Why: full SQL dumps with image blobs are large; compression reduces storage and download overhead without changing restore compatibility (decompress then import).
- Decision: allow administrators to delete completed/failed backups (file + history row) while blocking deletion of running jobs.
- Why: operators need lifecycle control and disk-space management while preserving integrity of in-flight backup operations.

## 2026-11-03 - Guided Capture Source Choice and HEIF Metadata Support

- Decision: expose both source actions for every guided-capture slot (`Choose file from gallery` and `Capture with camera`) instead of camera-only capture controls.
- Why: camera-intent capture in mobile browsers can skip camera-roll persistence and has inconsistent metadata behavior; explicit source choice is clearer and more flexible across mobile and desktop devices.
- Decision: for `Capture with camera`, first attempt in-browser camera capture (`getUserMedia`) and fall back to file-input capture intent when browser/device support is unavailable.
- Why: desktop browsers often ignore input `capture` hints; direct browser camera access provides clearer and more consistent camera behavior.
- Decision: add a fifth optional guided-capture slot tagged `Reference`.
- Why: users need to upload supporting reference images alongside box/completed photos in the same guided flow.
- Decision: add HEIF/HEIC decoder registration (`pillow-heif`) so EXIF/capture-time extraction can work when supported by source files.
- Why: guided capture and gallery uploads increasingly include HEIF/HEIC assets from modern phones, and metadata extraction quality depends on codec support.

## 2026-11-06 - Open Source License Selection (AGPL-3.0)

- Decision: license Jigsaurium under **GNU Affero General Public License v3.0 (AGPL-3.0)**.
- Why: project direction favors strong copyleft and preserving user freedoms for both redistributed and network-hosted modified versions.
- Why: AGPL aligns with a web-application/API deployment model where SaaS use is a primary distribution path.

## 2026-11-06 - Simple Mode Default Profile (no STFD, AI/embeddings disabled)

- Decision: define a documented Simple Mode profile for quick-start and evaluation with `STFD_ENABLED=0`, `AI_ENABLED=0`, and `IMAGE_EMBEDDINGS_ENABLED=0` by default.
- Why: reduces startup friction and removes external identity/AI dependency requirements for first-run usage.
- Decision: require UI suppression of controls tied to disabled AI/embedding capabilities.
- Why: avoids dead-end controls and improves first-run usability.

## 2026-11-06 - Quick-Start Datastore Strategy (SQLite local + MariaDB primary)

- Decision: adopt SQLite as the recommended datastore for local Simple Mode quick-start.
- Decision: keep MariaDB as the primary test/production datastore baseline.
- Why: SQLite reduces first-run operational overhead without requiring a second persistence model.
- Why: this preserves SQLAlchemy + Alembic migration patterns and avoids NoSQL model divergence.
- Impact: CI and maintainer validation must continue to guard against engine-specific SQL behavior differences.

## 2026-11-06 - Canonical Host Enforcement Policy

- Decision: enforce canonical host at the app layer with `CANONICAL_HOST_ENFORCEMENT=strict`, returning `421 Misdirected Request` for host mismatches.
- Why: runtime traffic is proxy-terminated but proxy controls may be outside direct ownership; app-layer enforcement closes direct-IP/backdoor host gaps.
- Decision: provide `CANONICAL_HOST_ENFORCEMENT=off` as an explicit opt-out for local/dev contributor workflows.
- Why: open-source/local setups may not always have canonical DNS/host routing available.

## 2026-11-08 - In-Frame Jigsaw Detail Overlay

- Decision: add a reusable in-frame "Jigsaw details" overlay panel in the SPA (instead of full-page navigation or browser popup).
- Why: image-library and image-browser workflows need quick context switching to inspect one jigsaw and return immediately without losing filters, scroll state, or current image position.
- Decision: make jigsaw references (for example in image-browser status and jigsaw inventory title cells) open that overlay.
- Why: users can move directly from image cleanup/assignment context to full per-jigsaw detail (metadata, assigned images, diary entries) with fewer clicks and less disorientation.

## 2026-11-12 - Edge and Authentication Hardening After Public Release

- Decision: trust exactly one forwarding header family, chosen by `TRUSTED_PROXY_HEADER` (`x-forwarded` by default, `forwarded` opt-in), and read right-most values only. This replaces "prefer RFC7239 `Forwarded`, fall back to `X-Forwarded-*`".
- Why: most Nginx setups set only `X-Forwarded-*` and pass a client's own `Forwarded` header through, so preferring `Forwarded` let any client choose its IP, host and scheme (bypassing login throttling and IP bans, or getting another IP banned).
- Decision: run the container with gunicorn (one threaded worker, see `gunicorn.conf.py`) instead of `flask run`.
- Why: the Werkzeug development server is not built for hostile traffic; one process keeps the in-process background jobs, embedding model and 404-streak tracker working unchanged.
- Decision: add an email-wide login failure limit across all client IPs (30 per 15 minutes) and run a dummy password-hash check for unknown accounts.
- Why: the per-(IP, email) limit alone did not bound attempts spread across many IPs, and response timing revealed which emails had accounts.
- Decision: verify upload bytes decode as a supported raster image, store the detected MIME type, and never serve original bytes to guests when derivatives are missing.
- Why: the declared multipart/zip type is client-controlled, so members could otherwise host arbitrary files publicly on the app's domain.
- Fix: import `DecompressionBombError` from `PIL.Image`. Under Pillow 13 the old `from PIL import DecompressionBombError` failed, which silently disabled Pillow in the API routes, so derivatives were never generated and guests were served original uploads (including EXIF location data). A regression test now asserts Pillow is loaded and guest previews carry no GPS EXIF.
- Decision: require `SECRET_KEY` of at least 32 characters outside dev.
- Why: the signed session cookie must resist offline guessing; 16 characters was too low a floor.
- Decision: refuse requests whose socket peer is not in `TRUSTED_PROXY_CIDRS` (`REQUIRE_TRUSTED_PROXY`, on by default; loopback and `GET /api/v1/health` exempt; inactive while no proxy CIDRs are set).
- Why: the published container port is reachable from the LAN, bypassing the reverse proxy. Binding the port to one address does not limit who can connect, and the deployments do not control a host firewall. All environments, including dev, run behind the proxy.
