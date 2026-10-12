# Changelog

This file records every notable change to the project, newest first, in Keep a Changelog format.
Work in progress collects under Unreleased and moves to a dated version section when a release branch is cut.
Versions follow semantic versioning; before 1.0 each milestone is a minor release.

## [Unreleased]

## [0.10.2] - 2026-10-12

The copilot's older Streamlit app is removed, and the architecture page's challenge check is current.

### Removed
- The copilot's older Streamlit app (`src/backend/copilot/ui`), its page test, and `make app`; the React app is the
  only copilot UI. The summary rules it shared with the API keep their tests in `tests/copilot/test_impact_summary.py`.

### Changed
- The architecture page's challenge check reflects 12 October: deployed, team confirmed, evaluation 8/8, deck in the
  repo; the video and the public repository remain.

## [0.10.1] - 2026-10-12

The story opens on scarcity, not prediction, and the deck is in the repo as a PDF.

### Changed
- The story opens on scarcity, not prediction: "At 2 a.m., two machines need the last spare part. OSI decides who gets
  it, covers the other, and proves it paid off." Updated in the README, the write-up, the architecture page, the demo
  script's opening and close, and the deck's cover and problem slides.

### Added
- The submission deck as a PDF in `docs/OSI-deck.pdf`, linked from the README and the write-up. The video link is
  still a placeholder on its last slide.

## [0.10.0] - 2026-10-12

Teammate review: ask about an inspection in place, and operator verdicts on false alerts that never silence later ones.

### Added
- **Ask about this** on the field inspection: a conversation with the copilot in place, with suggested questions.
  Follow-ups carry the alert and the last three turns, and every answer streams and is checked like any other run.
- **Operator verdict** on every alert: mark it as false with a reason. Later alerts on the same asset and failure
  mode show a caution and the agents ask for an inspection before spending, but the alert is never hidden. The
  verdicts reach the agents through `get_field_reports`; the track record and the impact analysis never read them.
  The supplier inbox's Reset also clears them.

## [0.9.0] - 2026-10-12

Live on Google Cloud: the first Cloud Run deploy, the full Gemini evaluation, and the write-up for the judges.

### Added
- The app is live on Cloud Run in `asia-southeast1`, with Gemini on Vertex AI; the link is in the README.
- The full evaluation on Gemini: 8/8 with `gemini-3.8-flash` on Vertex AI.

### Changed
- The README opens with the live link, where to click first, the evaluation score, and the stack, and adds how a
  real plant connects.
- `docs/SUBMISSION.md` is rewritten around the four judging criteria, technical merit first, with the live link,
  the 8/8 evaluation, a scalability path, and how a real plant would connect.
- The deploy script defaults to `asia-southeast1`, near the judges, and retries the role grant while a new service
  account becomes visible to IAM.
- The road to submission in `techdebt.md`: the team is confirmed, so step 1 is closed; the deploy and the live team run are done too.

## [0.8.2] - 2026-10-02

Inspection photos checked by Gemini, and the road to submission.

### Added
- The road to submission in `techdebt.md`: five ordered steps from confirming the team to submitting.
- Five inspection photos in `demo/field/photos`, each read by Gemini on its alert. Three worn parts are confirmed;
  the gearbox at 25 Jul 02:00, a false alert in the data, is not; a photo of the wrong part is flagged as such.

## [0.8.1] - 2026-10-02

The app's own name, CI, and a plain-language architecture page.

### Changed
- The app is now called OSI (Opsight Intelligence), replacing the working name, in the app header and page title,
  the API title, the docs, and the frontend package name.

### Added
- CI on GitHub Actions: `make setup`, `make lint`, and `make test` on Python 3.11 and Node 22, started by hand from
  the Actions tab to save minutes.
- `docs/architecture.html`: the product in plain language (problem, loop, system and agent-team diagrams, one alert
  start to finish, glossary) and a check of every official requirement and judging criterion against the repository.

## [0.8.0] - 2026-09-30

The finals-grade product: React and FastAPI, the track record, live mode, the closed loop, multimodal Gemini, and the agent team.

### Added
- `GEMINI_FALLBACK_MODELS`: when a Gemini model is out of quota or unavailable, the run restarts on the next backup
  model and the trace says so.
- Provider errors in plain language (quota, overloaded, credentials, model unavailable), each with what to do; the raw
  text sits behind a details toggle.
- Operations team on the Agent Development Kit: a `ParallelAgent` of three specialists (maintenance, procurement,
  customer service), each with only its role's tools and a brief in session state, then an operations lead in a
  `SequentialAgent` who reads the briefs and proposes. `mode=team` on the stream endpoint; the plan button, the
  autopilot, and a switch on the Copilot page use it.
- Every trace step carries its author; specialists' briefs show as their own cards.
- Multimodal Gemini: a structured reader in the gateway (images and PDFs in, schema-checked JSON out; other providers
  refuse clearly).
- Supplier inbox: Gemini reads supplier messages into delivery updates that revise open orders from the moment they
  arrive; three sample messages in `demo/field/inbox` (a delay, a confirmation, a price list).
- Field inspection: Gemini vision reads an inspection photo against the alert's failure mode; findings show on the
  alert and reach the agent through the new `get_field_reports` tool.
- Closed loop: approved proposals become decisions that change stock and queues from their moment on (a transfer leaves
  the sister shelf at once and arrives when promised; covered alerts stop competing for the spare).
- Outcomes settle once the clock passes the real failure or the end of the warning window: hours down with and without
  the plan, and the money saved. They show on the Approvals page and in the live feed with the approval and arrival.
- Approve and reject in the autopilot panel; Reset demo; `GET /api/proposals/outcomes`, `POST /api/proposals/reset`.
- Live mode (the Live page): the demo clock runs at 1, 3, or 6 hours per second; a plant event feed streams alerts,
  breakdowns, restorations, and spare orders and receipts; with the autopilot on, every alert that opens a work order
  pauses the clock while Gemini triages it and creates a proposal, then the clock runs on.
- `GET /api/events` and the pure event feed rules; alerts attached to an existing order are marked as covered.
- Value backtest (`make value`, `GET /api/value`, the Track record page): every alert of the test period analysed as it
  was raised and scored at its real outcome, the copilot against the site acting alone. On the default data: net
  197,949 USD, 662.1 h of downtime avoided, 1,860 USD spent on false alerts.
- React frontend in `src/frontend/` (Vite, TypeScript, Tailwind, Recharts): control room, a copilot page with the
  agent's tool calls streamed live, approvals, and How it works; `make web` with a dev proxy to `make api`.
- The backend serves the built frontend with client-side routes, so one Cloud Run service hosts the whole app.
- Frontend unit tests (Vitest) for formatting and the event-stream parser; `make lint` and `make test` cover both sides.
- The impact endpoint returns the baseline option, so the frontend does not repeat that rule.
- HTTP API (FastAPI, `make api`): health, engine status, scenarios, overview with headline, alert impact and
  evidence, proposals with approval, and the agent run streamed as server-sent events.
- `stream_copilot` yields each agent step as it happens; `run_copilot` is built on it.
- Scenarios and headline summaries now live in the copilot core, shared by the API and the apps.

### Changed
- README, plan, submission write-up, demo script, handover, and techdebt rewritten for the 0.8.0 scope; the inspection
  photo prompts are recorded in `demo/field/README.md`.
- The deploy script passes `GEMINI_FALLBACK_MODELS` to Cloud Run (with "@" as the list separator, since the value has
  commas).
- The autopilot stops itself and pauses the clock on quota or credential errors, with a banner, instead of failing on
  every new alert.
- The track record scores the analysis without demo approvals, so approving in the app never changes it.
- `create_app` takes the frontend build directory, so tests never depend on a local build.
- Negative money renders as "−$620".
- The container builds the frontend in a Node stage and serves everything with uvicorn instead of Streamlit.
- Python packages live under `src/backend/`, leaving `src/frontend/` for the React app; imports are unchanged.

### Fixed
- The Streamlit page test used the live proposals file, so a demo approval broke it; `default_services` now takes the
  proposals path and the test passes an empty temporary one.

## [0.7.0] - 2026-09-30

Milestones 0.2.0 to 0.7.0 were built together on develop and ship in this one release.

### Added
- `docs/SUBMISSION.md`: the write-up against the five judging points, with the architecture diagram and honest limits.
- `docs/DEMO_SCRIPT.md`: the three-minute demo, click by click.
- `Dockerfile`: a self-contained image that generates both worlds, the bridge, and the failure model at build time
  and serves the app on Cloud Run's port.
- `deploy/cloudrun.sh` (`make deploy`): enables the APIs, creates a service account limited to Vertex AI, and deploys
  from source with Gemini on Vertex AI; `make image` runs the container locally.
- `docs/HANDOVER.md`: the step-by-step move to Google Cloud, with checks, costs, teardown, and troubleshooting.
- `.streamlit/config.toml`: light theme, no usage statistics.
- Web app (`make app`): demo clock with named scenarios, control room with headline savings, spare conflicts,
  supplier record, priced options, customers at risk and sensor evidence, the Ask tab with verified answers and
  traces, Approvals, and How it works.
- Presenter tests, and a headless test of the real page on the generated data (skipped without data).
- Operations agent on the Agent Development Kit: Gemini by default, a local model through LiteLLM as the fallback;
  `make ask Q="..."` at the demo clock (`DEMO_AS_OF`, default 2026-07-25 02:00).
- Eight point-in-time tools: open alerts, impact analysis, sensor evidence, supplier record (governed
  `supplier_otd`), OEE summary, failures, work order history, and `propose_action_plan`.
- Action proposals that wait for approval in `data/copilot/proposals.json`, with numbers taken from the impact report.
- Answer verification: every number in the final answer must appear in a tool result.
- Agent evaluation (`make eval`): eight scenarios scored on tools, phrases, numbers, and proposals.
- `semantic/bridge/bridge.yaml`: sites to supply plants, components to spares with suppliers and min/max policies,
  urgent transfer terms, lines to customer parts with their contribution, and the customer-risk rule.
- Bridge builder (`make bridge`): validates every bridge id against both worlds, then simulates each site's spares
  store from the plant's repair history, with order lateness drawn from each supplier's delivery record.
- Impact analysis (`make impact A=<alert>`): point-in-time spare position with the queue of open alerts, supplier
  reliability from the governed `supplier_otd` metric, priced recovery options, customer order lines at risk, and a
  worst case learned only from past alert outcomes.
- `llm_gateway` package: one `LLMClient` interface with a Gemini adapter (google-genai, AI Studio key or Vertex AI) and
  the OpenAI-compatible local adapter. `LLM_PROVIDER` chooses between them.
- The Gemini adapter retries rate limits and server errors with capped exponential backoff, and reports an empty reply
  with its finish reason.
- `--provider`, `--model`, and `--base-url` on every command that calls a model; evaluation reports record the provider.

### Changed
- The default Gemini model is `gemini-3.8-flash`; `gemini-2.5-flash` is no longer offered to new users.
- The container starts Streamlit with exec, so Cloud Run's shutdown signal reaches it; Cloud Run memory is 2 GiB,
  since the running app uses about 400 MiB.
- The app is named emoldinounited.
- The agent's model calls retry rate limits and server errors with backoff (five attempts), for free-tier quotas.
- Both component packages build their model client through the gateway; their own model settings are gone.

### Fixed
- A model failure (quota, overload, permission) no longer crashes an agent run: the run records the provider's status
  line, the app shows it, and the evaluation scores the case as a model error.
- The supplier tool returns the window length (`window_days`), so an answer quoting "the last 90 days" verifies.
- scikit-learn is pinned to 1.7: version 1.9 trained a different classifier (31 of 41 failures caught at 0.32 false
  alerts per asset-month instead of the documented 27 of 41 at 0.16).

## [0.1.0] - 2026-09-30

### Added
- `pdm_oee` package, imported from pdm-oee-command-center v0.8.3, with its governed files in `semantic/pdm/`, data in
  `data/pdm/`, and tests in `tests/pdm_oee/`.
- `supply_ontology` package, imported from supply-chain-ontology v0.7.2, with its governed files in `semantic/supply/`,
  data in `data/supply/`, demo recipes in `demo/supply/`, and tests in `tests/supply_ontology/`.
- One Makefile: `make data` builds both worlds; component targets carry a `pdm-` or `supply-` prefix; `make settings`
  prints the resolved model endpoint and data directories.
- `docs/plan.md` with the problem, architecture, milestones, and judging criteria; component references in
  `docs/components/`.

### Changed
- Settings are namespaced per package (`PDM_DATA_DIR`, `SUPPLY_DATA_DIR`, and the matching semantic and seed
  variables), so both packages run in one process.
- Python 3.11 is the minimum; pandas is pinned below 3 because 3.0 turns None into NaN in string columns.
