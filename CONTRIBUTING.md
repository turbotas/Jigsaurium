# Contributing to Jigsaurium

Thanks for your interest in contributing.

This project uses documented specs and guardrails. Please read these first:

1. `Documentation/README.md`
2. `Documentation/product-spec.md`
3. `Documentation/architecture.md`
4. `Documentation/api-contract.md`
5. `Documentation/domain-rules.md`
6. `Documentation/operations-and-security.md`
7. `Documentation/design-system.md`
8. `Documentation/decisions.md`

## Ground rules

- Keep changes small and reviewable.
- Keep behavior aligned with existing specs.
- If behavior must change, update docs in the same change.
- Do not edit vendored GOV.UK source directly.
- Enforce authorization in backend APIs, not UI only.
- Add/update tests for behavior changes.

## Local setup

- Windows (dev profile): `scripts\setup_venv.bat dev`
- Linux/macOS (dev profile): `./scripts/setup_venv.sh dev`

Apply migrations before running app/tests:

- Windows: `.venv\Scripts\python.exe -m alembic upgrade head`
- Linux/macOS: `.venv/bin/python -m alembic upgrade head`

## Run tests

- Full: `scripts\run_tests.bat` or `./scripts/run_tests.sh`
- Functional only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m functional -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m functional -p no:cacheprovider`
- UI only:
  - Windows: `.venv\Scripts\python.exe -m pytest -m ui -p no:cacheprovider`
  - Linux/macOS: `.venv/bin/python -m pytest -m ui -p no:cacheprovider`

## Pull requests

Please use the PR template and include:

- What changed and why
- Related issue(s)
- Test evidence (commands + results)
- Docs/spec updates (if needed)

## Security and conduct

- Security reporting: `SECURITY.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Maintainer contact/governance path: `GOVERNANCE.md`
