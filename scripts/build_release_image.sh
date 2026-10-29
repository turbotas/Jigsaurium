#!/usr/bin/env sh
set -eu

VERSION="${1:-}"
OWNER="${2:-}"
IMAGE_NAME="${3:-jigsaurium}"

if [ -z "$VERSION" ] || [ -z "$OWNER" ]; then
  echo "Usage: ./scripts/build_release_image.sh <version> <owner> [image_name]"
  echo "Example: ./scripts/build_release_image.sh v0.1.0 my-github-org"
  exit 1
fi

echo "$VERSION" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || {
  echo "ERROR: version must match SemVer tag format, e.g. v1.2.3"
  exit 1
}

echo "$OWNER" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9-]*$' || {
  echo "ERROR: owner must be a GitHub username or organization (not a domain name)."
  exit 1
}

SHORT_SHA="$(git rev-parse --short=12 HEAD)"
FULL_SHA="$(git rev-parse HEAD)"
BUILD_TIME="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
OWNER_LOWER="$(printf '%s' "$OWNER" | tr '[:upper:]' '[:lower:]')"
IMAGE="ghcr.io/${OWNER_LOWER}/${IMAGE_NAME}"

echo
echo "Building ${IMAGE}:${VERSION}"
echo "Commit  : ${FULL_SHA}"
echo "Built at: ${BUILD_TIME}"
echo

if [ "${GHCR_SKIP_LOGIN:-0}" = "1" ]; then
  echo "Skipping docker login because GHCR_SKIP_LOGIN=1."
elif [ -n "${GHCR_TOKEN:-}" ]; then
  LOGIN_USER="${GHCR_USERNAME:-$OWNER}"
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$LOGIN_USER" --password-stdin
else
  echo "GHCR_TOKEN not set. Using existing Docker credential store session for ghcr.io."
fi

docker buildx build --platform linux/amd64 \
  --build-arg APP_VERSION="$VERSION" \
  --build-arg APP_BUILD_SHA="$FULL_SHA" \
  --build-arg APP_BUILD_TIME="$BUILD_TIME" \
  -t "${IMAGE}:${VERSION}" \
  -t "${IMAGE}:sha-${SHORT_SHA}" \
  --push .

echo
echo "Release image pushed: ${IMAGE}:${VERSION}"
echo "SHA tag pushed      : ${IMAGE}:sha-${SHORT_SHA}"
