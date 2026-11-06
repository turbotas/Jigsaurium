# Third-Party Notices

This project includes third-party software under their respective licenses.

## Project license

- Jigsaurium: **AGPL-3.0-only** (see [`LICENSE`](LICENSE))

## Direct third-party dependencies (key runtime/build)

### Python

- Flask — BSD-3-Clause
- SQLAlchemy — MIT
- Alembic — MIT
- PyMySQL — MIT
- PyJWT — MIT
- Pillow — MIT-CMU
- pillow-heif — BSD-3-Clause
- torch (CPU wheel) — Apache-2.0, BSD-family, MIT, ISC, Zlib (multi-license expression)
- transformers — Apache-2.0

### Python (dev/test)

- pytest — MIT
- python-dotenv — BSD-3-Clause
- playwright — Apache-2.0

### Node / frontend tooling

- govuk-frontend (vendored assets under `app/static/vendor/govuk`) — MIT

## Compatibility review summary

As of 2026-11-06, direct dependency licenses reviewed for this repository are permissive or weak-copyleft licenses compatible with AGPL-3.0 distribution in this project context.

No direct dependency was identified as imposing a known license conflict with AGPL-3.0 for Jigsaurium distribution.

## Attribution and source

- Python package licenses are declared in package metadata from installed distributions and/or upstream package indexes.
- npm package license metadata for `govuk-frontend` is sourced from npm registry metadata.

Where upstream packages require preserving copyright, license, or NOTICE text, those obligations remain with the respective upstream package terms.
