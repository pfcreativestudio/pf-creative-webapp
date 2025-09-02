#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

# Deploy to Cloud Run (managed)
gcloud run deploy "$SERVICE" \
  --image="$IMAGE_LATEST" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances="$SQL_INST" \
  --set-env-vars="FRONTEND_BASE_URLS=${FRONTENDS},INSTANCE_CONNECTION_NAME=${SQL_INST},DB_USER=postgres,DB_NAME=postgres" \
  --set-secrets="DB_PASSWORD=db_password:latest,JWT_SECRET=jwt_secret:latest,ADMIN_PASSWORD=admin_password:latest" \
  --memory=512Mi \
  --timeout=300

# Print URL
URL=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')
echo "SERVICE URL: $URL"