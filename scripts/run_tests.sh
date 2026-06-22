#!/usr/bin/env sh
set -eu

VENV_PYTHON=".venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Run ./scripts/setup_venv.sh first."
  exit 1
fi

"$VENV_PYTHON" -m pytest -p no:cacheprovider "$@"
