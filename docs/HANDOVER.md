# Handover: from this laptop to Google Cloud

This is the checklist for moving emoldinounited onto Google Cloud once the team has an account.
Everything the app needs already runs locally; the cloud steps are one-off setup plus one deploy script.
Work top to bottom; each step says how to check it worked.

## 0. Where things stand

| Piece | State |
|---|---|
| Plant and supply worlds, bridge, impact analysis, track record | Done, tested, reproducible from seeds |
| Gemini through the model gateway, with backup models | Done; AI Studio key locally, Vertex AI on Cloud Run |
| Agents (Agent Development Kit): single agent and the four-agent team | Done; evaluated locally, verified live on single Gemini runs |
| Multimodal: supplier inbox (live on Gemini), inspection photos (waiting for sample photos) | Done |
| Web app: React frontend over FastAPI, one container | Done; image built and served locally |
| Cloud Run deploy script | Written; not yet run against a real project |

## 1. Local check with Gemini (no Cloud account needed)

1. Get a key at https://aistudio.google.com (a personal Google login is enough). In `.env`, set `GEMINI_API_KEY=...`
   and `LLM_PROVIDER=gemini`, and keep `GEMINI_FALLBACK_MODELS` as in `.env.example`. Never commit `.env`.
2. `make settings` should print `LLM_PROVIDER=gemini` and the Gemini model.
3. `make api` and `make web`, then open http://localhost:5173. On the Copilot page, a question should end with the
   green "Verified" line.
4. The free tier allows about 20 requests per model per day; a single-agent run takes about five and a team run about
   twelve. The backup models stretch that about four times. For `make eval` and rehearsals, use a paid key or step 4.

## 2. Google Cloud account and project

1. Use a personal Google account (not a work account) at https://console.cloud.google.com.
2. Create a project, for example `emoldinounited-2026`, and note its project id.
3. Attach billing: the free trial, or the competition credits once they arrive.
4. **Set a budget alert first:** Billing, then Budgets and alerts, then a budget of 20 USD with alerts at 50%, 90%,
   and 100%.

## 3. Tools on the laptop

1. Install the Google Cloud CLI: https://cloud.google.com/sdk/docs/install (on macOS,
   `brew install --cask google-cloud-sdk`).
2. `gcloud auth login`, then `gcloud config set project <project id>`.
3. Optional local container check: start Docker Desktop, then `make image` and open http://localhost:8080. The first
   build takes several minutes, because it builds the frontend and generates all the data.

## 4. Deploy to Cloud Run

```bash
PROJECT_ID=<project id> make deploy
```

The script (`deploy/cloudrun.sh`) is safe to re-run. It:
- enables Cloud Run, Cloud Build, Artifact Registry, and Vertex AI
- creates the service account `ops-copilot-run` and grants it `roles/aiplatform.user` only
- builds the container with Cloud Build and deploys the service `ops-copilot` in `europe-west1`: 2 CPUs, 2 GiB (the
  running app uses about 400 MiB), session affinity, and public access for the judges
- sets `GOOGLE_GENAI_USE_VERTEXAI=true`, so Gemini is called on Vertex AI with the service account (no API key is
  deployed), and passes `GEMINI_MODEL` and `GEMINI_FALLBACK_MODELS`
- prints the service URL

Overrides: `REGION`, `VERTEX_LOCATION` (default `global`), `GEMINI_MODEL`, `GEMINI_FALLBACK_MODELS`, `SERVICE`,
`MIN_INSTANCES`.

**Check, in this order:**
1. `<url>/health` returns `{"status":"ok"}`, and `<url>/api/engine-status` shows `"ready":true` and the model.
2. The Control room at the bearing scenario shows 3 open alerts, 2 spare conflicts, 180.3 h and $93.2k avoided.
3. The Track record shows a net of $197.9k.
4. On the Copilot page, a question comes back verified. Then "Draft the plan with the copilot" on US1-L2-01 runs the
   four-agent team to a proposal. This also clears the "live team run" item in `techdebt.md`.
5. The logs (`gcloud run services logs read ops-copilot --region europe-west1`) show no permission errors from
   Vertex AI.
6. Run `make eval` against Vertex AI (point a local `.env` at the project with `GOOGLE_GENAI_USE_VERTEXAI=true`,
   `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`, after `gcloud auth application-default login`), and record the
   score in the README.

## 5. While the judges are looking

- `MIN_INSTANCES=1 PROJECT_ID=<id> make deploy` keeps one instance warm; a cold start loads the data in about
  20 seconds. Set it back to 0 afterwards to stop the cost.
- Proposals, inspections, and supplier updates live in the container's file system and reset when an instance
  restarts. **Reset demo** on the Approvals page and **Reset** on the Supplier inbox page give a clean start.

## 6. Costs and teardown

- Cloud Run with `MIN_INSTANCES=0` costs nothing while idle. Gemini Flash costs cents per agent run; a team run costs
  about twice a single run.
- To remove everything: `gcloud run services delete ops-copilot --region europe-west1`, then delete the images in
  Artifact Registry (repository `cloud-run-source-deploy`), or shut the whole project down.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Gemini refused the credentials" | The service account lacks `roles/aiplatform.user`, or the Vertex AI API is off; re-run the script |
| "The model ... is not available" | The model is not offered at `VERTEX_LOCATION`; try `VERTEX_LOCATION=us-central1` or another `GEMINI_MODEL` |
| "The Gemini quota ... is used up" | Quota; the app switches to the backup models, and the autopilot stops itself when none is left |
| "Gemini ... is overloaded" | A temporary 503 on Google's side; try again in a minute |
| The page reloads or loses state | Session affinity missing, or the instance restarted; re-run the script |
| The build runs out of memory | Raise the Cloud Build machine type, or build locally and push the image |
