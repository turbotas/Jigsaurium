# Jigsaurium

Jigsaurium is a self-hostable web app for managing a jigsaw collection, tracking completion history, and organizing puzzle images.

It is built as a Flask JSON API (`/api/v1`) with a SPA frontend and is designed for home/small-group use with clear role-based access controls and auditability.

## Who this is for

- Individuals or households managing a shared jigsaw collection
- Developers/operators who want a self-hosted inventory + completion diary workflow
- Contributors who want to extend a Python/Flask + SPA codebase with documented API/domain rules

## What you can do (current baseline)

- Maintain jigsaw inventory (create/update/retire/restore)
- Upload and manage jigsaw/image-library photos
- Track per-jigsaw completion diary entries (date, difficulty, notes)
- Use role-based access for admin/member/legacy borrower compatibility
- Run optional AI-assisted metadata extraction and image-similarity workflows (feature-flagged)

## Documentation map

- Product scope: `Documentation/product-spec.md`
- Architecture: `Documentation/architecture.md`
- API contract: `Documentation/api-contract.md`
- Domain/permission rules: `Documentation/domain-rules.md`
- Operations/security: `Documentation/operations-and-security.md`
- Simple mode profile: `Documentation/simple-mode.md`
- Design system guidance: `Documentation/design-system.md`
- Architecture decisions: `Documentation/decisions.md`

Start with `Documentation/README.md` for the full documentation index.

## Project layout

```
Jigsaurium/
  app/
    static/
      css/
      js/
      images/
    templates/
    __init__.py
    routes.py
  instance/
  Documentation/
  environments/
  requirements/
  scripts/
  tests/
  .gitignore
  config.py
  requirements.txt
  run.py
```

## Quick start

If needed on Linux/macOS, make helper scripts executable: `chmod +x scripts/*.sh`.

1. Create a virtual environment and install dependencies.
   - Windows (dev profile): `scripts\setup_venv.bat dev`
   - Linux/macOS (dev profile): `./scripts/setup_venv.sh dev`
   - Windows (prod profile): `scripts\setup_venv.bat prod`
   - Linux/macOS (prod profile): `./scripts/setup_venv.sh prod`
2. Create local environment file:
    - Copy `environments/dev.env.example` to `environments/dev.env.local`.
    - Optional convenience for `run.py`: also copy `environments/dev.env.local` to `.env`.
   - Keep secrets in `*.local` files only (git-ignored).
3. Apply migrations to your configured database:
   - Windows: `.venv\Scripts\python.exe -m alembic upgrade head`
   - Linux/macOS: `.venv/bin/python -m alembic upgrade head`
4. Run the app:
    - Windows: `run.bat`
    - Linux/macOS: `./run.sh`
   - Direct Python alternative: `.venv/bin/python run.py` (Linux/macOS) or `.venv\Scripts\python.exe run.py` (Windows)
   - Startup scripts now warn when the configured database appears behind the latest Alembic head.
    - In `APP_ENV=dev`, startup scripts also run dependency freshness checks (Python packages + GOV.UK frontend npm status).
    - Set `STARTUP_UPDATE_CHECK=0` to skip startup dependency checks.

### Simple Mode quick start (recommended first run)

Simple Mode starts with local defaults that avoid external integrations:

- SQLite file database (`instance/jigsaurium-simple.db`)
- STFD disabled
- AI create-from-image disabled
- Image embeddings/similarity disabled

Run with one command:

- Windows: `scripts\run_simple.bat`
- Linux/macOS: `./scripts/run_simple.sh`

Note: run setup first (`scripts\setup_venv.bat dev` or `./scripts/setup_venv.sh dev`).

Simple Mode defaults to skipping dependency freshness checks to keep first-run startup fast.
To opt in, set `STARTUP_UPDATE_CHECK=1` before launching `run_simple`.

## GOV.UK Frontend assets

- Vendored assets are stored under `app/static/vendor/govuk`.
- Local style overrides must stay in `app/static/css/styles.css`.
- Update vendored GOV.UK assets:
  - Windows: `scripts\update_govuk_assets.bat`
  - Linux/macOS: `./scripts/update_govuk_assets.sh`
  - Optional explicit version: `scripts\update_govuk_assets.bat 6.2.0` or `./scripts/update_govuk_assets.sh 6.2.0`
  - UNC path fallback: `.venv\Scripts\python.exe scripts\vendor_govuk_assets.py --update 6.2.0`
- Dev startup performs a GOV.UK version freshness check and warns if npm has a newer release.
- Set `GOVUK_VERSION_CHECK=0` to disable the startup warning check.

## Environment configuration

- Git-safe templates are stored in `environments/*.example`.
- Sensitive values go in `environments/*.local` and are ignored by Git.
- Root `.env` is optional for local runs (`run.py` loads it when present); prefer maintaining `environments/dev.env.local` as the source file.
- Environment templates available:
  - `environments/dev.env.example`
  - `environments/test.env.example`
  - `environments/prod.env.example`
- Build/release metadata variables are supported:
  - `APP_VERSION` (for example `v1.2.3`)
  - `APP_BUILD_SHA` (source commit SHA)
  - `APP_BUILD_TIME` (UTC build timestamp)
- Environment/version/build metadata is shown in the UI footer and in `GET /api/v1/health`.
- Startup performs runtime configuration validation and fails fast with actionable messages for invalid values (for example malformed numeric env vars or unsupported `DB_BACKUP_COMPRESSION`).

## API

- Base path: `/api/v1`
- Contract and payload/error conventions: `Documentation/api-contract.md`
- Health check: `GET /api/v1/health`

## Embedding model prefetch

- Prefetch the pinned embedding model into the local vendored path:
  - Windows: `.venv\Scripts\python.exe scripts\prefetch_embedding_model.py`
  - Linux/macOS: `.venv/bin/python scripts/prefetch_embedding_model.py`
- Optional overrides:
  - `--revision <commit-or-tag>`
  - `--target-dir <path>`
  - `--token <hf_token>` (or set `HF_TOKEN`)
  - `--keep-existing` (incremental refresh)

## Testing

- Run all tests:
  - Windows: `scripts\run_tests.bat`
  - Linux/macOS: `./scripts/run_tests.sh`
- Run functional tests only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m functional -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m functional -p no:cacheprovider`
- Run non-functional tests only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m nonfunctional -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m nonfunctional -p no:cacheprovider`
- GUI smoke tests are included in pytest as marker `ui`.
- Install browser runtime once per machine for GUI tests:
  - Windows: `.venv\Scripts\python.exe -m playwright install chromium`
  - Linux/macOS: `.venv/bin/python -m playwright install chromium`
- Run GUI tests only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m ui -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m ui -p no:cacheprovider`
- Run embedding runtime tests only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m embedding -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m embedding -p no:cacheprovider`
- CI runs automatically with GitHub Actions:
  - `API and Core Tests` runs `pytest -m "not ui"` on pushes and pull requests.
  - `UI Smoke Tests` runs `pytest -m ui` on pull requests and pushes to `main`.
  - `Embedding Runtime Tests` also runs separately (manual/weekly) as a dedicated focused workflow.
  - Workflows include a package guard that fails if any `nvidia-*` or `cuda-*` pip dependency is installed.
- Note: test scripts disable pytest cache provider (`-p no:cacheprovider`) to avoid Windows network-share permission issues at test finalization.
- Published test quality/scope policy is documented in `Documentation/operations-and-security.md` ("Test Quality Statement (M3 Step 3.2)").
- Troubleshooting:
  - If `ModuleNotFoundError: No module named 'flask'` appears in tests, Python is not using this repo's virtual environment.
  - Confirm interpreter path before debugging dependencies: `py -3 -c "import sys; print(sys.executable)"` and `.venv\Scripts\python.exe -c "import flask; print('ok')"`.
  - On UNC paths, `.bat` wrappers can print a `CMD.EXE ... UNC paths are not supported` warning. Use direct `.venv` Python commands when needed.

## Admin credential bootstrap

- The bootstrap script mirrors app runtime loading by reading root `.env` when present.
- Set `DATABASE_URL` to your persistent target database (not `:memory:`), or pass it directly with `--database-url`.
- Apply schema migrations before bootstrapping:
  - `.venv\Scripts\python.exe -m alembic upgrade head` (Windows)
  - `.venv/bin/python -m alembic upgrade head` (Linux/macOS)
  - Important: run migrations with the same `DATABASE_URL` that bootstrap will use.
  - If `DATABASE_URL` is missing, Alembic now fails fast instead of migrating in-memory SQLite.
- Create the first admin account:
  - `.venv\Scripts\python.exe scripts\bootstrap_admin.py --email admin@example.com` (Windows)
  - `.venv/bin/python scripts/bootstrap_admin.py --email admin@example.com` (Linux/macOS)
- Direct DB override example:
  - `.venv\Scripts\python.exe scripts\bootstrap_admin.py --email admin@example.com --database-url "sqlite+pysqlite:///instance/jigsaurium.db"`
- Optional explicit env file example:
  - `.venv\Scripts\python.exe scripts\bootstrap_admin.py --email admin@example.com --env-file "environments/dev.env.local"`
- Password is prompted securely and must be at least 12 characters.
- To rotate an existing admin password, re-run with `--reset-password`.

## Demo seed and reset workflow

For evaluator/quick-start environments, you can populate predictable demo records and reset back to a clean state.

- Prerequisite: run migrations first against the same database:
  - Windows: `.venv\Scripts\python.exe -m alembic upgrade head`
  - Linux/macOS: `.venv/bin/python -m alembic upgrade head`

- Seed demo data (users, jigsaws, images, diary entries, and one active loan):
  - Windows: `.venv\Scripts\python.exe scripts\seed_demo_data.py --password "DemoPassword123!" --reset-first`
  - Linux/macOS: `.venv/bin/python scripts/seed_demo_data.py --password "DemoPassword123!" --reset-first`

- Reset mutable app data (keeps baseline roles):
  - Windows: `.venv\Scripts\python.exe scripts\reset_demo_data.py`
  - Linux/macOS: `.venv/bin/python scripts/reset_demo_data.py`

- Optional DB/env overrides for both commands:
  - `--database-url "sqlite+pysqlite:///instance/jigsaurium-simple.db"`
  - `--env-file "environments/dev.env.local"`

- Seeded demo user emails:
  - `admin@example.com`
  - `member@example.com`
  - `borrower@example.com`
  - All seeded users use the same password value passed via `--password`.

## Dependency updates

- Check outdated dependencies:
  - Windows: `scripts\check_updates.bat`
  - Linux/macOS: `./scripts/check_updates.sh`
- Update check scripts report both Python package updates and GOV.UK frontend pinned/installed/latest versions.
- Targeted Python dependency updates with known-good lock refresh:
  - Full profile promotion (recommended):
    - Windows: `scripts\update_python_dependencies.bat`
    - Linux/macOS: `./scripts/update_python_dependencies.sh`
  - This upgrades everything resolvable in the selected profile, runs tests (dev profile), then rewrites requirement minimums to tested installed versions and refreshes known-good lock.
  - Optional targeted mode:
    - Windows: `scripts\update_python_dependencies.bat Flask==3.1.1`
    - Linux/macOS: `./scripts/update_python_dependencies.sh Flask==3.1.1`
  - Multiple targets: `scripts\update_python_dependencies.bat Flask==3.1.1 SQLAlchemy==2.0.37`
  - Default dev test gate: full suite (`pytest -p no:cacheprovider`).
  - When `playwright` is installed in the dev profile, the workflow auto-runs `python -m playwright install chromium` before tests to avoid UI skips due to missing browser binaries.
  - Optional opt-out: `--skip-playwright-install`.
  - Optional custom gate example: `scripts\update_python_dependencies.bat --test-cmd "-m pytest -p no:cacheprovider -q"`
  - Prod profile option: `scripts\update_python_dependencies.bat --profile prod PyMySQL==1.1.1`

## Container release helpers

- Build and push a SemVer release image:
  - Windows: `scripts\build_release_image.bat v0.1.0 YOUR_ORG`
  - Linux/macOS: `./scripts/build_release_image.sh v0.1.0 YOUR_ORG`
- Default release images are CPU-only and include core embedding runtime dependencies.
- Promote pointer tags (`dev`, `test`, `prod`) to a release tag or digest:
  - Windows: `scripts\promote_pointer_tag.bat YOUR_ORG test v0.1.0`
  - Linux/macOS: `./scripts/promote_pointer_tag.sh YOUR_ORG test v0.1.0`
- Container startup can auto-run schema migrations with `AUTO_MIGRATE=1` (recommended for empty test/prod databases).

## Dependency files

- `requirements/base.txt`: shared runtime dependencies.
- `requirements/prod.txt`: production install set (no pytest).
- `requirements/dev.txt`: developer/test install set (includes pytest).
- `requirements/embeddings.txt`: core embedding runtime dependencies pinned to CPU-only PyTorch wheel index (no CUDA/NVIDIA packages).
- `requirements/known-good-dev.txt`: exact tested dependency lock for dev/test installs.
- `requirements/known-good-prod.txt`: exact tested dependency lock for production profile installs.
- `requirements.txt`: compatibility alias to production dependencies.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.
See [`LICENSE`](LICENSE).

Third-party attribution and license notes are documented in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Changelog

- Project release notes follow Semantic Versioning and are tracked in [`CHANGELOG.md`](CHANGELOG.md).

## Community and Governance

- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Code of Conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Maintainer contact and governance basics: [`GOVERNANCE.md`](GOVERNANCE.md)
