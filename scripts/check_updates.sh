#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

echo "Python package update status:"
PIP_OUTDATED_OUTPUT="$($PYTHON_BIN -m pip list --outdated || true)"
if [ -n "$PIP_OUTDATED_OUTPUT" ]; then
  echo "$PIP_OUTDATED_OUTPUT"
else
  echo "  All Python packages are up to date"
fi

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
