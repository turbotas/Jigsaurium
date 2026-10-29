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

### Build and publish release image

- Trigger by creating and pushing a tag that matches `v*` (for example `v1.2.3`).
- Workflow builds a container image and publishes it to GHCR.
- Release tags are published as immutable image tags.

Local equivalents are available for operators:

- Windows: `scripts\\build_release_image.bat`
- Linux/macOS: `./scripts/build_release_image.sh`

### Promote environment pointers

- Trigger manually with `workflow_dispatch`.
- Input the source release reference (`v1.2.3` by tag or `sha256:...` digest).
- Input the target pointer (`dev`, `test`, or `prod`).
- Workflow updates the pointer tag to point to the same image.

Local equivalents are available for operators:

- Windows: `scripts\\promote_pointer_tag.bat`
- Linux/macOS: `./scripts/promote_pointer_tag.sh`

This avoids rebuilding during promotion.

## Recommended Promotion Sequence

1. Build and publish release image for `vX.Y.Z`.
2. Promote `dev` pointer to `vX.Y.Z` and run smoke tests.
3. Promote `test` pointer to `vX.Y.Z` and run acceptance tests.
4. Promote `prod` pointer to `vX.Y.Z` after approval.

## Deployment Recommendation

- Prefer deployment by digest for production when possible.
- Keep `prod` pointer for operator convenience.
- Store deployment records including: env, version tag, digest, SHA, and deployment time.
