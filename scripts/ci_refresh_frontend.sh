#!/usr/bin/env sh
# Called by .github/workflows/deps-refresh.yml (Node is set up from .nvmrc first).
# Jigsaurium: update GOV.UK Frontend to the newest release within its current major version,
# re-vendor it, and bring the SBOM extra components and THIRD_PARTY_NOTICES.md to the same
# version (tests/test_sbom_report.py checks they match package.json). A new major version is
# only reported in the job summary.
set -eu

npm ci --no-audit --no-fund
major="$(node -p "require('./package.json').devDependencies['govuk-frontend'].split('.')[0]")"
target="$(npm view "govuk-frontend@^${major}" version --json \
  | python -c 'import json, sys; v = json.load(sys.stdin); print(v[-1] if isinstance(v, list) else v)')"
latest="$(npm view govuk-frontend version)"
echo "GOV.UK Frontend target: ${target} (latest overall: ${latest})"
if [ "${latest%%.*}" != "$major" ]; then
  echo "GOV.UK Frontend ${latest} is a new major version; not applied automatically." >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"
fi
python scripts/vendor_govuk_assets.py --update "$target"
python scripts/sync_sbom_extra_versions.py
