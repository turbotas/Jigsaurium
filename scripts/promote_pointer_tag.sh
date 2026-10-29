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

OWNER_LOWER="$(printf '%s' "$OWNER" | tr '[:upper:]' '[:lower:]')"
IMAGE="ghcr.io/${OWNER_LOWER}/${IMAGE_NAME}"

case "$SOURCE_REF" in
  sha256:*) SOURCE_IMAGE="${IMAGE}@${SOURCE_REF}" ;;
  *) SOURCE_IMAGE="${IMAGE}:${SOURCE_REF}" ;;
esac

echo "Promoting ${SOURCE_IMAGE} -> ${IMAGE}:${POINTER}"

docker login ghcr.io
docker buildx imagetools create -t "${IMAGE}:${POINTER}" "${SOURCE_IMAGE}"

echo "Promotion completed: ${IMAGE}:${POINTER}"
