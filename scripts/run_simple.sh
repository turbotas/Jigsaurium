#!/usr/bin/env sh
set -eu

VENV_PYTHON=".venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Run ./scripts/setup_venv.sh first."
  exit 1
fi

mkdir -p instance

export APP_ENV="${APP_ENV:-dev}"
export SECRET_KEY="${SECRET_KEY:-change-me-dev}"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///instance/jigsaurium-simple.db}"

export STFD_ENABLED="0"
export STFD_ALLOW_LOCAL_LOGIN="0"
export AI_ENABLED="0"
export IMAGE_EMBEDDINGS_ENABLED="0"

export AI_API_KEY=""
export AI_ENDPOINT_URL=""
export AI_MODEL=""
export HF_TOKEN=""

"$VENV_PYTHON" scripts/warn_if_migrations_pending.py

if [ "$APP_ENV" = "dev" ] && [ "${STARTUP_UPDATE_CHECK:-0}" = "1" ]; then
  echo
  echo "Dependency freshness check:"
  if ! sh ./scripts/check_updates.sh; then
    echo "WARNING: Dependency update check encountered an issue; continuing startup."
  fi
fi

if [ "$APP_ENV" = "dev" ]; then
  APP_ENV="$APP_ENV" "$VENV_PYTHON" -m flask --app run:app run --host 0.0.0.0 --reload --no-debugger
else
  APP_ENV="$APP_ENV" "$VENV_PYTHON" -m flask --app run:app run --host 0.0.0.0
fi
