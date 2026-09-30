# Handover: from this laptop to Google Cloud

This is the checklist for moving the operations copilot onto Google Cloud once the team has an account.
Everything the app needs already runs locally. The cloud steps are one-off setup plus one deploy script.
Work top to bottom; each step says how to check it worked.

## 0. Where things stand

| Piece | State |
|---|---|
| Plant and supply worlds, bridge, impact analysis | Done, tested, reproducible from seeds |
| Gemini through the model gateway | Done; runs with an AI Studio key locally, Vertex AI on Cloud Run |
| Operations agent (Agent Development Kit) | Done; evaluated with `make eval` |
| Web app | Done; `make app` |
| Container and Cloud Run deploy script | Written (`Dockerfile`, `deploy/cloudrun.sh`); not yet run against a real project |

## 1. Local check with Gemini (no Cloud account needed)

1. Get a key at https://aistudio.google.com (a personal Google login is enough) and add it to `.env`:
   `GEMINI_API_KEY=...` and `LLM_PROVIDER=gemini`. Never commit `.env`.
2. `make settings` should print `LLM_PROVIDER=gemini` and the Gemini model.
3. `make ask Q="Which alerts need attention right now?"` should end with `[verified; tools: ...]`.
4. `make eval` runs the eight agent scenarios and writes `data/copilot/eval/<model>.json`. Record the score in the README.

## 2. Google Cloud account and project

1. Create or choose a personal Google account (not a work account) and open https://console.cloud.google.com.
2. Create a project, for example `ops-copilot-2026`, and note its project id.
3. Attach billing: the free trial, or the competition credits once they arrive.
4. **Set a budget alert first:** Billing, then Budgets and alerts, then a budget of 20 USD with alerts at 50%, 90%, and 100%.

## 3. Tools on the laptop

1. Install the Google Cloud CLI: https://cloud.google.com/sdk/docs/install (on macOS, `brew install --cask google-cloud-sdk`).
2. `gcloud auth login`, then `gcloud config set project <project id>`.
3. Optional local container check: start Docker Desktop, then `make image` and open http://localhost:8080. This uses
   the Gemini key from `.env`. The first build takes several minutes because it generates all the data.

## 4. Deploy to Cloud Run

```bash
PROJECT_ID=<project id> make deploy
```

The script (`deploy/cloudrun.sh`) is safe to re-run. It:
- enables Cloud Run, Cloud Build, Artifact Registry, and Vertex AI
- creates the service account `ops-copilot-run` and grants it `roles/aiplatform.user` only
- builds the container with Cloud Build and deploys the service `ops-copilot` in `europe-west1` with 2 CPUs, 4 GiB,
  session affinity (Streamlit keeps a websocket per viewer), and public access for the judges
- sets `GOOGLE_GENAI_USE_VERTEXAI=true`, so Gemini is called on Vertex AI with the service account; no API key is deployed
- prints the service URL

Overrides: `REGION`, `VERTEX_LOCATION` (default `global`), `GEMINI_MODEL`, `SERVICE`, `MIN_INSTANCES`.

**Check:** open the URL. The control room should show 3 open alerts for the bearing scenario. On the Ask tab, a
question should come back verified. In the logs (`gcloud run services logs read ops-copilot --region europe-west1`)
there should be no permission errors from Vertex AI.

## 5. While the judges are looking

- `MIN_INSTANCES=1 PROJECT_ID=<id> make deploy` keeps one instance warm. The first load builds the OEE engine in
  memory and takes about 20 seconds on a cold start. Set it back to 0 afterwards to stop the cost.
- Proposals are stored in the container's file system, so approvals reset when an instance restarts. That is
  acceptable for a demo, and is listed in `techdebt.md`.

## 6. Costs and teardown

- Cloud Run with `MIN_INSTANCES=0` costs nothing while idle. Gemini Flash costs cents per agent run.
- To remove everything: `gcloud run services delete ops-copilot --region europe-west1`, then delete the images in
  Artifact Registry (repository `cloud-run-source-deploy`), or shut the whole project down.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `PERMISSION_DENIED` from Vertex AI | The service account lacks `roles/aiplatform.user`, or the Vertex AI API is off; re-run the script |
| `404` for the model | The model name is not offered at `VERTEX_LOCATION`; try `VERTEX_LOCATION=us-central1` or another `GEMINI_MODEL` |
| `429 RESOURCE_EXHAUSTED` | Quota; the gateway retries with backoff, and a few seconds between questions helps |
| The page reloads or loses state | Session affinity missing, or the instance restarted; re-run the script |
| Build runs out of memory | Raise the Cloud Build machine type, or build locally and push the image |
