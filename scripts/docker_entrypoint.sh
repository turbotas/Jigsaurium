#!/usr/bin/env sh
set -eu

if [ "${AUTO_MIGRATE:-1}" = "1" ]; then
  echo "Running database migrations (alembic upgrade head)..."
  python -m alembic upgrade head
fi

exec "$@"
