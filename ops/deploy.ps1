# PowerShell equivalent of deploy.sh
$ErrorActionPreference = "Stop"

# Source environment variables (PowerShell equivalent)
$PROJECT = if ($env:PROJECT) { $env:PROJECT } else { "pf-studio-prod" }
$REGION = if ($env:REGION) { $env:REGION } else { "asia-southeast1" }
$SERVICE = if ($env:SERVICE) { $env:SERVICE } else { "pfsystem-api" }
$REPO = if ($env:REPO) { $env:REPO } else { "pfsystem" }
$SQL_INST = if ($env:SQL_INST) { $env:SQL_INST } else { "pf-studio-prod:asia-southeast1:pf-database-new" }
$FRONTENDS = if ($env:FRONTENDS) { $env:FRONTENDS } else { "https://pfcreativeaistudio.vercel.app,https://pf-creative-webapp.vercel.app,http://localhost:3000" }

# Image tags
$IMAGE_TAG = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { (git rev-parse --short HEAD) }
$IMAGE = "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:${IMAGE_TAG}"
$IMAGE_LATEST = "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"

Write-Host "Deploying to Cloud Run..." -ForegroundColor Cyan

# Deploy to Cloud Run (managed)
gcloud run deploy $SERVICE `
  --image=$IMAGE_LATEST `
  --region=$REGION `
  --platform=managed `
  --allow-unauthenticated `
  --add-cloudsql-instances=$SQL_INST `
  --set-env-vars="FRONTEND_BASE_URLS=${FRONTENDS},INSTANCE_CONNECTION_NAME=${SQL_INST},DB_USER=postgres,DB_NAME=postgres" `
  --set-secrets="DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest" `
  --memory=512Mi `
  --timeout=300

# Print URL
$URL = gcloud run services describe $SERVICE --region=$REGION --format='value(status.url)'
Write-Host "SERVICE URL: $URL" -ForegroundColor Green
