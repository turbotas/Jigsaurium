#!/usr/bin/env sh
set -eu

OWNER="${1:-}"
POINTER="${2:-}"
SOURCE_REF="${3:-}"
IMAGE_NAME="${4:-jigsaurium}"

if [ -z "$OWNER" ] || [ -z "$POINTER" ] || [ -z "$SOURCE_REF" ]; then
  echo "Usage: ./scripts/promote_pointer_tag.sh <owner> <pointer> <source_ref> [image_name]"
  echo "Example: ./scripts/promote_pointer_tag.sh my-github-org test v0.1.0"
  echo "Example: ./scripts/promote_pointer_tag.sh my-github-org prod sha256:abc123..."
  exit 1
fi

case "$POINTER" in
  dev|test|prod) ;;
  *)
    echo "ERROR: pointer must be one of: dev, test, prod"
    exit 1
    ;;
esac

echo "$OWNER" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9-]*$' || {
  echo "ERROR: owner must be a GitHub username or organization (not a domain name)."
  exit 1
}

OWNER_LOWER="$(printf '%s' "$OWNER" | tr '[:upper:]' '[:lower:]')"
IMAGE="ghcr.io/${OWNER_LOWER}/${IMAGE_NAME}"

case "$SOURCE_REF" in
  sha256:*) SOURCE_IMAGE="${IMAGE}@${SOURCE_REF}" ;;
  *) SOURCE_IMAGE="${IMAGE}:${SOURCE_REF}" ;;
esac

echo "Promoting ${SOURCE_IMAGE} -> ${IMAGE}:${POINTER}"

if [ "${GHCR_SKIP_LOGIN:-0}" = "1" ]; then
  echo "Skipping docker login because GHCR_SKIP_LOGIN=1."
elif [ -n "${GHCR_TOKEN:-}" ]; then
  LOGIN_USER="${GHCR_USERNAME:-$OWNER}"
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$LOGIN_USER" --password-stdin
else
  echo "GHCR_TOKEN not set. Using existing Docker credential store session for ghcr.io."
fi
docker buildx imagetools create -t "${IMAGE}:${POINTER}" "${SOURCE_IMAGE}"

echo "Promotion completed: ${IMAGE}:${POINTER}"
