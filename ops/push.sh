#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
docker push "$IMAGE"
docker push "$IMAGE_LATEST"
