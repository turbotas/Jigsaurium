# Jigsaurium

Starter Flask project scaffold using the app factory pattern.

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
  .env.example
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
   - Copy `.env.example` to `.env`, or
   - Copy `environments/dev.env.example` to `environments/dev.env.local`.
3. Run the app:
   - Windows: `run.bat`
   - Linux/macOS: `./run.sh`
   - Direct Python alternative: `.venv/bin/python run.py` (Linux/macOS) or `.venv\Scripts\python.exe run.py` (Windows)

## GOV.UK Frontend assets

- Vendored assets are stored under `app/static/vendor/govuk`.
- Local style overrides must stay in `app/static/css/styles.css`.
- Update vendored GOV.UK assets:
  - Windows: `scripts\update_govuk_assets.bat`
  - Linux/macOS: `./scripts/update_govuk_assets.sh`
  - Optional explicit version: `scripts\update_govuk_assets.bat 6.2.0` or `./scripts/update_govuk_assets.sh 6.2.0`
- Dev startup performs a GOV.UK version freshness check and warns if npm has a newer release.
- Set `GOVUK_VERSION_CHECK=0` to disable the startup warning check.

## Environment configuration

- Git-safe templates are stored in `environments/*.example`.
- Sensitive values go in `environments/*.local` and are ignored by Git.
- Environment templates available:
  - `environments/dev.env.example`
  - `environments/test.env.example`
  - `environments/prod.env.example`

## Testing

- Run all tests:
  - Windows: `scripts\run_tests.bat`
  - Linux/macOS: `./scripts/run_tests.sh`
- Run functional tests only: `python -m pytest -m functional`
- Run non-functional tests only: `python -m pytest -m nonfunctional`
- Note: test scripts disable pytest cache provider (`-p no:cacheprovider`) to avoid Windows network-share permission issues at test finalization.

## Dependency updates

- Check outdated dependencies:
  - Windows: `scripts\check_updates.bat`
  - Linux/macOS: `./scripts/check_updates.sh`

## Dependency files

- `requirements/base.txt`: shared runtime dependencies.
- `requirements/prod.txt`: production install set (no pytest).
- `requirements/dev.txt`: developer/test install set (includes pytest).
- `requirements.txt`: compatibility alias to production dependencies.
