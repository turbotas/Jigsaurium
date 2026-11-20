#!/usr/bin/env sh
# Called by .github/workflows/deps-refresh.yml (Node is set up from .nvmrc first).
# Jigsaurium: update GOV.UK Frontend to the newest release within its current major version and
# re-vendor it.
set -eu

npm ci --no-audit --no-fund
major="$(node -p "require('./package.json').devDependencies['govuk-frontend'].split('.')[0]")"
target="$(npm view "govuk-frontend@^${major}" version --json \
  | python -c 'import json, sys; v = json.load(sys.stdin); print(v[-1] if isinstance(v, list) else v)')"
echo "GOV.UK Frontend target: ${target}"
python scripts/vendor_govuk_assets.py --update "$target"
