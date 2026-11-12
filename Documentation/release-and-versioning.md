# Release and Versioning

This project uses a SemVer release model with mutable environment pointers for deployment convenience.

## Goals

- Keep immutable release history (`vMAJOR.MINOR.PATCH`).
- Support quick environment promotion (`dev`, `test`, `prod` pointers).
- Expose deployed environment and build version in the UI and health API.

## Semantic Versioning Policy (Step 3.3)

Jigsaurium follows **SemVer 2.0.0** using `vMAJOR.MINOR.PATCH` tags.

- **PATCH** (`v1.2.3` -> `v1.2.4`)
  - Backward-compatible bug fixes
  - Security fixes that do not break documented API contracts
  - Documentation-only changes (when a release is still desired)
- **MINOR** (`v1.2.3` -> `v1.3.0`)
  - Backward-compatible feature additions
  - New endpoints/fields that do not break existing clients
  - Operational additions that remain compatible with existing deployment contracts
- **MAJOR** (`v1.2.3` -> `v2.0.0`)
  - Backward-incompatible API or behavior changes
  - Breaking schema/contract changes requiring client or operator migration action

Version tags are immutable once published.

### Automatic patch releases

Every commit that reaches `master` with CI passing is built once by `build-image.yml` and gets a
version automatically:

- If the commit already carries a `vX.Y.Z` tag, that version is used.
- Otherwise the highest `vX.Y.Z` tag gets its **patch** bumped (`v0.2.3` -> `v0.2.4`). A
  pre-release tag is finalised instead (`v0.2.0-rc1` -> `v0.2.0`).
- After the image is published the commit is tagged and a GitHub Release with generated notes is
  created. The image is published as `vX.Y.Z` and `sha-<12>`; `test` is moved to it, and `prod`
  after approval in the `prod` Environment.

To start a new **minor** or **major** line, push the tag (for example `v0.3.0`) on the latest
`master` commit; the following builds continue with `v0.3.1`, `v0.3.2`, ... Weekly dependency
refreshes count as patch releases, consistent with the policy above.

## Tagging Model

### Immutable release tags

- `v1.0.0`
- `v1.0.1`
- `v1.1.0`

Never move these tags after release.

### Mutable environment pointers

- `dev`
- `test`
- `prod`

These pointers can move to newer release images after validation.

## Runtime Build Metadata

The app supports these environment variables:

- `APP_ENV` (`dev`, `test`, `prod`)
- `APP_VERSION` (for example `v1.2.3`)
- `APP_BUILD_SHA` (git SHA)
- `APP_BUILD_TIME` (UTC timestamp)

This metadata is visible in two places:

- UI footer on all HTML pages.
- `GET /api/v1/health` response.

## Changelog Policy

- Canonical changelog file: `CHANGELOG.md` at repository root.
- Format: **Keep a Changelog** style sections (`Added`, `Changed`, `Fixed`, `Removed`, `Security`).
- Version headings must map to SemVer tags (for example `## [v1.3.0] - 2026-11-06`).
- Include an `Unreleased` section for merged but not yet tagged work.
- Every release tag created in this repository should have a corresponding changelog entry in the same change set (or immediately prior when release automation consumes an already-prepared entry).

## GitHub Release Workflows

This project's standard release path is GitHub Actions only.

Workflows expected for release operations:

- `CI`
- `Container Release`
- `Promote Pointer Tag`
- `Embedding Runtime Tests`

### Build and publish release image

- First push release commits to default branch: `git push origin master`.
- Then create and push a tag that matches `v*` (for example `v1.2.3`).
- Workflow builds a container image and publishes it to GHCR.
- Release tags are published as immutable image tags.

### Promote environment pointers

- Trigger manually with `workflow_dispatch`.
- Input the source release reference (`v1.2.3` by tag or `sha256:...` digest).
- Input the target pointer (`dev`, `test`, or `prod`).
- Workflow updates the pointer tag to point to the same image.
- Use the workflow filename for CLI dispatch consistency:
  - `gh workflow run promote-pointer-tag.yml -f source_ref=v1.2.3 -f target_pointer=test`

This avoids rebuilding during promotion and avoids local GHCR auth drift.

## Recommended Promotion Sequence

1. Push `master` to remote.
2. Build and publish immutable release image for `vX.Y.Z`.
3. Promote `test` pointer to `vX.Y.Z` and run acceptance tests.
4. Promote `prod` pointer to `vX.Y.Z` after approval.

## Release Checklist (Step 3.4)

Use this checklist for every release candidate and production release.

### Pre-release checks

1. Confirm repository is on the intended release commit/branch (`master`).
2. Run required tests locally or confirm latest CI pass:
   - API/core tests (`pytest -m "not ui"`)
   - UI smoke tests (`pytest -m ui`)
   - Embedding tests (`pytest -m embedding`) when embedding/runtime behavior changed
3. Ensure migrations are current and clean (`alembic upgrade head` against target DB).
4. Verify no pending doc/spec mismatches for release-affecting behavior.

### Build and publish immutable release tag

1. Choose SemVer tag `vX.Y.Z`.
2. Push release commit and tag:
   - `git push origin master`
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
3. Verify `Container Release` workflow completed successfully and published:
   - `ghcr.io/<owner>/jigsaurium:vX.Y.Z`
   - `ghcr.io/<owner>/jigsaurium:sha-<12-char-sha>`

### Promote environment pointers

1. Promote `test` pointer to release image.
2. Run acceptance checks in test environment.
3. Promote `prod` pointer after approval.

CLI dispatch examples:

- `gh workflow run promote-pointer-tag.yml -f source_ref=vX.Y.Z -f target_pointer=test`
- `gh workflow run promote-pointer-tag.yml -f source_ref=vX.Y.Z -f target_pointer=prod`

### Post-release verification

1. Confirm `/api/v1/health` reports expected `APP_ENV`, `APP_VERSION`, `APP_BUILD_SHA`, `APP_BUILD_TIME`.
2. Confirm UI footer build metadata matches expected release.
3. Record deployment details (environment, tag, digest, commit, timestamp).

## Dry-Run Record (Step 3.4)

Date: 2026-11-06

Performed non-destructive dry-run validation of release tooling and workflow presence.

### Workflow presence check

Verified active workflows include:

- `CI`
- `Container Release`
- `Promote Pointer Tag`
- `Embedding Runtime Tests`

### Script guardrail dry-runs

Validated release helper input checks without publishing artifacts:

- `scripts\build_release_image.bat v1.2 demo-org`
  - Expected/observed: fails fast with `VERSION must match SemVer tag format, e.g. v1.2.3`.
- `scripts\promote_pointer_tag.bat demo-org qa v1.2.3`
  - Expected/observed: fails fast with `pointer must be one of: dev, test, prod`.

Outcome: release process documentation and guardrails are in place; dry-run completed without performing live image publish/promotion.

## Deployment Recommendation

- Prefer deployment by digest for production when possible.
- Keep `prod` pointer for operator convenience.
- Store deployment records including: env, version tag, digest, SHA, and deployment time.
