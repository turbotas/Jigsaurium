# Release and Versioning

This project uses a SemVer release model with mutable environment pointers for deployment convenience.

## Goals

- Keep immutable release history (`vMAJOR.MINOR.PATCH`).
- Support quick environment promotion (`dev`, `test`, `prod` pointers).
- Expose deployed environment and build version in the UI and health API.

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

## GitHub Release Workflows

This project's standard release path is GitHub Actions only.

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

## Deployment Recommendation

- Prefer deployment by digest for production when possible.
- Keep `prod` pointer for operator convenience.
- Store deployment records including: env, version tag, digest, SHA, and deployment time.
