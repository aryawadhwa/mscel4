#!/usr/bin/env bash
# deploy.sh — one-shot deploy to Cloud Run (backend) + Firebase Hosting (frontend)
# Usage: GCP_PROJECT=your-project-id ./deploy.sh
#
# Prerequisites:
#   gcloud auth login
#   gcloud auth application-default login
#   firebase login
#   gcloud services enable run.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com

set -euo pipefail

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT env var}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="debias-api"
FRONTEND_DIR="frontend"

echo "▶ Deploying backend to Cloud Run (project: $GCP_PROJECT, region: $GCP_REGION)"
gcloud run deploy "$SERVICE_NAME" \
  --source ./backend \
  --project "$GCP_PROJECT" \
  --region "$GCP_REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GCP_PROJECT,GOOGLE_CLOUD_LOCATION=$GCP_REGION" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300

BACKEND_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project "$GCP_PROJECT" \
  --region "$GCP_REGION" \
  --format "value(status.url)")

echo "✓ Backend deployed: $BACKEND_URL"

echo "▶ Building frontend (VITE_API_BASE=$BACKEND_URL)"
cd "$FRONTEND_DIR"
VITE_API_BASE="$BACKEND_URL" npm run build

echo "▶ Deploying frontend to Firebase Hosting"
npx firebase-tools deploy --only hosting --project "$GCP_PROJECT"

echo ""
echo "✅ Deploy complete"
echo "   Backend:  $BACKEND_URL"
echo "   Frontend: https://$GCP_PROJECT.web.app"
