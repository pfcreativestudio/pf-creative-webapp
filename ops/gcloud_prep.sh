#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

echo ">> gcloud login (browser will open if not logged in)"
gcloud auth login || true
gcloud config set project "$PROJECT"
gcloud config set run/region "$REGION"

echo ">> Enable required APIs (idempotent)"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com sqladmin.googleapis.com

echo ">> Ensure Artifact Registry repo exists (idempotent)"
gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" || true

echo ">> Configure docker for Artifact Registry"
gcloud auth configure-docker ${REGION}-docker.pkg.dev -q
