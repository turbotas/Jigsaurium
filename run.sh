#!/usr/bin/env sh
set -eu

VENV_PYTHON=".venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Run ./scripts/setup_venv.sh first."
  exit 1
fi

"$VENV_PYTHON" scripts/warn_if_migrations_pending.py

APP_ENV_VALUE="${APP_ENV:-dev}"
if [ "$APP_ENV_VALUE" = "dev" ]; then
  echo
  if [ "${STARTUP_VENV_SYNC:-1}" = "0" ]; then
    VENV_SYNC_FLAG=""
  else
    VENV_SYNC_FLAG="--sync"
  fi
  # shellcheck disable=SC2086
  if ! "$VENV_PYTHON" scripts/sync_dev_venv.py --profile dev $VENV_SYNC_FLAG; then
    echo "WARNING: The virtual environment differs from the dependency lock; continuing startup."
  fi
fi

if [ "$APP_ENV_VALUE" = "dev" ] && [ "${STARTUP_UPDATE_CHECK:-1}" != "0" ]; then
  echo
  echo "Dependency freshness check:"
  if ! sh ./scripts/check_updates.sh --no-python; then
    echo "WARNING: Dependency update check encountered an issue; continuing startup."
  fi
fi

APP_ENV="$APP_ENV_VALUE" "$VENV_PYTHON" run.py
