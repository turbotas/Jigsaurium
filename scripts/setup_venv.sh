#!/usr/bin/env sh
set -eu

VENV_DIR=".venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PROFILE="${1:-dev}"
REQ_FILE="requirements/${PROFILE}.txt"
KNOWN_GOOD_FILE="requirements/known-good-${PROFILE}.txt"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Could not find $VENV_DIR/bin/python"
  exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
  echo "Unknown dependency profile '$PROFILE'."
  echo "Expected one of: dev, prod"
  exit 1
fi

echo "Installing dependencies using profile: $PROFILE"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
if [ -f "$KNOWN_GOOD_FILE" ]; then
  echo "Applying known-good constraints: $KNOWN_GOOD_FILE"
  "$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE" -c "$KNOWN_GOOD_FILE"
else
  "$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"
fi

echo "Done. Activate with: source $VENV_DIR/bin/activate"
