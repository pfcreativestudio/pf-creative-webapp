#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
PREV=$(gcloud run revisions list --service="$SERVICE" --region="$REGION" --format='value(metadata.name)' --limit=2 | tail -n1)
echo "Rolling traffic to previous revision: $PREV"
gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-revisions="$PREV"=100
