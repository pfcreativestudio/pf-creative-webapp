#!/usr/bin/env bash
set -euo pipefail
PROJECT="pf-studio-prod"
REGION="asia-southeast1"
REPO="pfsystem"
IMAGE="pfsystem-api-app"
SERVICE="pfsystem-api-app"
INSTANCE="pf-database-new"
CONNECTION="${PROJECT}:${REGION}:${INSTANCE}"
FRONTEND_BASE_URL="https://pfcreativeaistudio.vercel.app"
DB_USER="postgres"
DB_NAME="postgres"
DB_PASSWORD_VAL='PFcreative@2025'
JWT_SECRET_VAL='d528502f7a76853766814ffd7bdad0d3577ef4c1273995402a2239493a5d19cd'
ADMIN_PASSWORD_VAL='PFcreative@2025'
GEMINI_API_KEY_VAL='AIzaSyDa8OIqUe79HMCglD92OmR3Fa_-pW70GbU'
BILLPLZ_API_KEY_VAL='f9478c0c-a6fc-444b-9132-69b144a7af47'
BILLPLZ_COLLECTION_ID_VAL='ek0rvdud'
BILLPLZ_X_SIGNATURE_VAL='02012c5e2e15131188ea0c34447e4b4aa65511e88ed48180347205ee74d5aff6537f91d64188af7c9c4059e5cc924395ae909d265ef26c010b9e16ed1fa920f2'
SA_NAME="run-pfsystem"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
TAG="$(date +%Y%m%d-%H%M)"
IMG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:${TAG}"
gcloud config set project "${PROJECT}" >/dev/null
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com sqladmin.googleapis.com >/dev/null
if ! gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPO}" --repository-format=docker --location="${REGION}" --description="PF API images"
fi
if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" --display-name="Cloud Run SA for ${SERVICE}"
fi
PROJECT_NUMBER="$(gcloud projects describe ${PROJECT} --format='value(projectNumber)')"
gcloud projects add-iam-policy-binding "${PROJECT}" --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor" >/dev/null || true
gcloud projects add-iam-policy-binding "${PROJECT}" --member="serviceAccount:${SA_EMAIL}" --role="roles/cloudsql.client" >/dev/null || true
gcloud artifacts repositories add-iam-policy-binding "${REPO}" --location="${REGION}" --project="${PROJECT}" --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" --role="roles/artifactregistry.reader" >/dev/null || true
ensure_secret () { local NAME="$1"; local VALUE="$2"; if gcloud secrets describe "${NAME}" >/dev/null 2>&1; then printf '%s' "${VALUE}" | gcloud secrets versions add "${NAME}" --data-file=- >/dev/null; else printf '%s' "${VALUE}" | gcloud secrets create "${NAME}" --data-file=- >/dev/null; fi; }
ensure_secret db_password            "${DB_PASSWORD_VAL}"
ensure_secret jwt_secret             "${JWT_SECRET_VAL}"
ensure_secret admin_password         "${ADMIN_PASSWORD_VAL}"
ensure_secret gemini_api_key         "${GEMINI_API_KEY_VAL}"
ensure_secret billplz_api_key        "${BILLPLZ_API_KEY_VAL}"
ensure_secret billplz_collection_id  "${BILLPLZ_COLLECTION_ID_VAL}"
ensure_secret billplz_x_signature    "${BILLPLZ_X_SIGNATURE_VAL}"
gcloud builds submit --tag "${IMG}"
gcloud run deploy "${SERVICE}" --image="${IMG}" --region="${REGION}" --platform=managed --service-account="${SA_EMAIL}" --allow-unauthenticated --add-cloudsql-instances="${CONNECTION}" --set-env-vars="DB_USER=${DB_USER},DB_NAME=${DB_NAME},INSTANCE_CONNECTION_NAME=${CONNECTION},FRONTEND_BASE_URL=${FRONTEND_BASE_URL},STRICT_SECRET_CHECK=1" --set-secrets="DB_PASSWORD=db_password:latest,JWT_SECRET=jwt_secret:latest,ADMIN_PASSWORD=admin_password:latest,GEMINI_API_KEY=gemini_api_key:latest,BILLPLZ_API_KEY=billplz_api_key:latest,BILLPLZ_COLLECTION_ID=billplz_collection_id:latest,BILLPLZ_X_SIGNATURE=billplz_x_signature:latest" --port=8080 --cpu=1 --memory=512Mi --concurrency=80 --min-instances=0 --max-instances=10 --ingress=all
SERVICE_URL="$(gcloud run services describe ${SERVICE} --region ${REGION} --format='value(status.url)')"
echo -e "
Cloud Run URL: ${SERVICE_URL}
"
curl -sS -m 10 "${SERVICE_URL}/healthz" || true; echo
curl -sS -m 20 -H "Content-Type: application/json" -d '{"session_id":"test","user_text":"hi"}' "${SERVICE_URL}/v1/director/chat" || true; echo
echo "[DONE] Backend deployed."
