#!/usr/bin/env bash
# Deploys the operations copilot to Cloud Run from source: Cloud Build builds the Dockerfile, Cloud Run serves it, and
# Gemini is reached on Vertex AI with the service's own service account, so no API key is stored anywhere.
# Idempotent: re-running updates the service. Usage: PROJECT_ID=my-project deploy/cloudrun.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project id}"
REGION="${REGION:-asia-southeast1}"              # Cloud Run region, near the JAPAC judges
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"     # Gemini endpoint location on Vertex AI
SERVICE="${SERVICE:-ops-copilot}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
# Backups when a model is unavailable; comma-separated, so the env list below uses "@" as its separator.
GEMINI_FALLBACK_MODELS="${GEMINI_FALLBACK_MODELS:-gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash}"
SA_NAME="${SA_NAME:-ops-copilot-run}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"              # set to 1 while judges are looking, to avoid cold starts
IAM_RETRIES=6                                    # a new service account takes a few seconds to become visible to IAM
IAM_RETRY_SECONDS=10
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Project ${PROJECT_ID}, region ${REGION}, service ${SERVICE}, model ${GEMINI_MODEL}"
gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com

if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" --display-name "Operations copilot on Cloud Run"
fi
for attempt in $(seq "${IAM_RETRIES}"); do
  if gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member "serviceAccount:${SA_EMAIL}" \
    --role roles/aiplatform.user --condition None >/dev/null; then
    break
  fi
  if [ "${attempt}" -eq "${IAM_RETRIES}" ]; then
    echo "Could not grant roles/aiplatform.user to ${SA_EMAIL}" >&2
    exit 1
  fi
  echo "Service account not visible to IAM yet; retrying in ${IAM_RETRY_SECONDS}s"
  sleep "${IAM_RETRY_SECONDS}"
done

gcloud run deploy "${SERVICE}" \
  --source . \
  --region "${REGION}" \
  --service-account "${SA_EMAIL}" \
  --set-env-vars "^@^LLM_PROVIDER=gemini@GEMINI_MODEL=${GEMINI_MODEL}@GEMINI_FALLBACK_MODELS=${GEMINI_FALLBACK_MODELS}@GOOGLE_GENAI_USE_VERTEXAI=true@GOOGLE_CLOUD_PROJECT=${PROJECT_ID}@GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION}" \
  --memory 2Gi --cpu 2 --timeout 900 --concurrency 20 \
  --min-instances "${MIN_INSTANCES}" --max-instances 3 \
  --session-affinity \
  --allow-unauthenticated

gcloud run services describe "${SERVICE}" --region "${REGION}" --format 'value(status.url)'
