# Simple Mode Specification (M2 Step 2.1)

## Goal

Define a low-friction default runtime profile for local evaluation and quick onboarding.

Simple Mode is intended to work without external identity providers or AI runtime dependencies.

## Scope

Simple Mode covers:

- authentication mode defaults
- AI and image-similarity feature defaults
- expected UI behavior when optional features are disabled
- required vs optional configuration for first run

Simple Mode datastore behavior is defined in Step 2.2 (`#34`) and documented below.

## Behavioral Requirements

1. Application must start and operate without STFD integration.
2. AI-assisted create/enrich capabilities are disabled by default.
3. Image embedding/similarity capabilities are disabled by default.
4. Disabled capabilities must not appear as actionable UI controls.
5. The remaining core inventory/diary/image-library workflows must remain usable.

## Feature Flag Matrix (Simple Mode defaults)

| Area | Setting | Default | Required in Simple Mode | Notes |
|---|---|---:|---:|---|
| Identity | `STFD_ENABLED` | `0` | Yes | Use local auth flow only. |
| Identity | `STFD_ALLOW_LOCAL_LOGIN` | `0` | Yes | Kept off when STFD is off; break-glass not needed. |
| AI metadata | `AI_ENABLED` | `0` | Yes | Disables create-from-image/enrich AI calls. |
| AI metadata | `AI_API_KEY` | empty | Yes | Must not be required when AI disabled. |
| Image similarity | `IMAGE_EMBEDDINGS_ENABLED` | `0` | Yes | Disables embedding backfill/similarity APIs. |
| Image similarity | `HF_TOKEN` | empty | Yes | Must not be required when embeddings disabled. |
| Bulk AI mode | `BULK_AI_CREATE_INLINE` | `0` | Recommended | Irrelevant while AI disabled; keep explicit default. |

## UI Expectations Under Simple Mode

When `AI_ENABLED=0` and `IMAGE_EMBEDDINGS_ENABLED=0`:

- Hide or suppress AI-driven actions (for example create-from-image/enrich-from-images controls that require AI).
- Hide or suppress embedding diagnostics/backfill/similarity controls.
- Do not show dead controls that return avoidable errors for disabled capabilities.

If a direct API call is made to a disabled feature, API behavior should remain explicit and contract-safe (for example clear conflict/disabled response).

## Configuration Contract

- Required baseline runtime variables remain those needed for core app operation (`DATABASE_URL`, `SECRET_KEY`, environment/runtime settings).
- STFD and AI/embedding provider credentials are optional in Simple Mode and should remain blank in example quick-start profiles.

## Runtime Profile Entry Point

Simple Mode is launched via dedicated startup scripts:

- Windows: `scripts\\run_simple.bat`
- Linux/macOS: `./scripts/run_simple.sh`

The profile sets (or defaults) the following runtime values:

- `DATABASE_URL=sqlite+pysqlite:///instance/jigsaurium-simple.db` (when not already set)
- `STFD_ENABLED=0`
- `STFD_ALLOW_LOCAL_LOGIN=0`
- `AI_ENABLED=0`
- `IMAGE_EMBEDDINGS_ENABLED=0`

## Evaluator Data Workflow (Step 2.6)

For quick demonstrations in Simple Mode, provide/reset local data with:

- Seed demo data:
  - Windows: `.venv\Scripts\python.exe scripts\seed_demo_data.py --password "DemoPassword123!" --reset-first`
  - Linux/macOS: `.venv/bin/python scripts/seed_demo_data.py --password "DemoPassword123!" --reset-first`
- Reset mutable records:
  - Windows: `.venv\Scripts\python.exe scripts\reset_demo_data.py`
  - Linux/macOS: `.venv/bin/python scripts/reset_demo_data.py`

These commands target the active `DATABASE_URL` (or explicit `--database-url` override) and are intended for local/test evaluator workflows.

## Quick-Start Verification (Step 2.8)

Date: 2026-11-06

Validated run-through on a clean local session path:

1. Create/install virtual environment (dev profile).
2. Apply migrations (`alembic upgrade head`).
3. Seed evaluator data (`scripts/seed_demo_data.py --reset-first`).
4. Launch Simple Mode (`scripts/run_simple.*`).
5. Verify health endpoint returns `200`.

Observed timing in this maintainer run-through:

- End-to-end (migrate + seed + app ready): **~17 seconds** on local machine.
- App-ready phase after launch command: **<1 second**.

### Friction points addressed

- **Migration step visibility**: quick-start documentation now explicitly includes `alembic upgrade head` before first launch.
- **Startup delay risk**: Simple Mode launch scripts now skip dependency freshness checks by default.\
  Maintainers can opt in with `STARTUP_UPDATE_CHECK=1`.

## Datastore Strategy (Step 2.2 decision)

### Decision

- **Recommended quick-start datastore**: SQLite (embedded file DB) for local/Simple Mode.
- **Primary production/test datastore remains**: MariaDB.

### Why this option

- Keeps SQLAlchemy + Alembic architecture unchanged.
- Minimizes first-run dependencies (no separate DB service needed for local onboarding).
- Preserves compatibility with existing schema, domain rules, and migration workflow.

### Options considered

1. Keep MariaDB-only for all modes
   - Pro: single datastore path
   - Con: higher local setup friction, weaker quick-start experience
2. Introduce NoSQL quick-start store
   - Pro: could be embedded depending on engine
   - Con: large architectural divergence from SQLAlchemy/Alembic model and current schema/migration practices
3. **SQLite for local quick-start + MariaDB for test/prod (selected)**
   - Pro: low-friction onboarding with minimal architecture change
   - Con: requires clear docs and testing discipline to avoid engine-specific drift

### Migration/compatibility impact assessment

- No domain model redesign required.
- Alembic migration workflow remains mandatory.
- Existing MySQL-compatible backup/export behavior remains authoritative for production operations.
- Engine differences (MariaDB vs SQLite) require ongoing CI/maintainer checks to catch SQL-dialect differences before release.
