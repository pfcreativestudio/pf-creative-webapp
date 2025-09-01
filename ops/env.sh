# ops/env.sh
export PROJECT=${PROJECT:-pf-studio-prod}
export REGION=${REGION:-asia-southeast1}
export SERVICE=${SERVICE:-pfsystem-api}
export REPO=${REPO:-pfsystem}
export SQL_INST=${SQL_INST:-pf-studio-prod:asia-southeast1:pf-database-new}
export FRONTENDS=${FRONTENDS:-https://pfcreativeaistudio.vercel.app,https://pf-creative-webapp.vercel.app,http://localhost:3000}

# Image tags
export IMAGE_TAG=${IMAGE_TAG:-$(git rev-parse --short HEAD)}
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:${IMAGE_TAG}"
export IMAGE_LATEST="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"
