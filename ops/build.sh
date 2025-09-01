#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
docker build -t "$IMAGE" -t "$IMAGE_LATEST" .
echo "Built images:"
echo "  $IMAGE"
echo "  $IMAGE_LATEST"
