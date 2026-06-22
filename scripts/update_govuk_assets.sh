#!/usr/bin/env sh
set -eu

VENV_PYTHON=".venv/bin/python"
TARGET_VERSION="${1:-latest}"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Run ./scripts/setup_venv.sh first."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to update GOV.UK frontend assets."
  exit 1
fi

"$VENV_PYTHON" scripts/vendor_govuk_assets.py --update "$TARGET_VERSION"
