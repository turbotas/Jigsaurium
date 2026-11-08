# Environment Configuration

This folder stores Git-safe environment templates for each runtime environment.

## Templates (committed)

- `dev.env.example`
- `test.env.example`
- `prod.env.example`

## Sensitive runtime files (not committed)

Create local files from templates and fill real values:

- `dev.env.local`
- `test.env.local`
- `prod.env.local`

These `*.local` files are ignored by Git.

## Usage

- Local development: load `environments/dev.env.local`.
- Test environment: load `environments/test.env.local`.
- Production environment: load `environments/prod.env.local`.
- Optional local convenience: copy `environments/dev.env.local` to repo-root `.env` when using `run.py` (it calls `python-dotenv` on startup).

## Notes

- `AUTO_MIGRATE` is used by container startup (`scripts/docker_entrypoint.sh`) to run `alembic upgrade head` before launching the app.
