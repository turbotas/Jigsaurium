#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

# First the venv against the reviewed lock (run.sh passes --no-python because it has already
# checked and synced it), then what is newer than that on PyPI, and how each would arrive.
if [ "${1:-}" != "--no-python" ]; then
  "$PYTHON_BIN" scripts/sync_dev_venv.py --profile dev || true
  echo
fi
"$PYTHON_BIN" scripts/report_newer_releases.py --profile dev || true

if command -v npm >/dev/null 2>&1; then
  echo
  echo "GOV.UK frontend npm update status:"
  GOVUK_PINNED="$(node -p "try { require('./package.json').devDependencies['govuk-frontend'] || '' } catch (e) { '' }")"
  GOVUK_INSTALLED="$(node -p "try { require('./node_modules/govuk-frontend/package.json').version || '' } catch (e) { '' }")"
  GOVUK_LATEST="$(npm view govuk-frontend version --silent 2>/dev/null || true)"

  if [ -n "$GOVUK_PINNED" ]; then
    echo "  Pinned   : $GOVUK_PINNED"
  else
    echo "  Pinned   : not set in package.json"
  fi

  if [ -n "$GOVUK_INSTALLED" ]; then
    echo "  Installed: $GOVUK_INSTALLED"
  else
    echo "  Installed: not installed"
  fi

  if [ -n "$GOVUK_LATEST" ]; then
    echo "  Latest   : $GOVUK_LATEST"
  else
    echo "  Latest   : unavailable"
  fi

  if [ -n "$GOVUK_INSTALLED" ] && [ -n "$GOVUK_LATEST" ]; then
    if [ "$GOVUK_INSTALLED" = "$GOVUK_LATEST" ]; then
      echo "  Status   : up to date"
    else
      echo "  Status   : update available"
    fi
  fi
else
  echo
  echo "GOV.UK frontend npm update status: npm unavailable"
fi
