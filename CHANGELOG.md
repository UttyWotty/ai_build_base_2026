# Changelog

This file records every notable change to the project, newest first, in Keep a Changelog format.
Work in progress collects under Unreleased and moves to a dated version section when a release branch is cut.
Versions follow semantic versioning; before 1.0 each milestone is a minor release.

## [Unreleased]

### Added
- `GEMINI_FALLBACK_MODELS`: when a Gemini model is out of quota or unavailable, the run restarts on the next backup
  model and the trace says so.
- Provider errors in plain language (quota, overloaded, credentials, model unavailable), each with what to do; the raw
  text sits behind a details toggle.

### Changed
- The autopilot stops itself and pauses the clock on quota or credential errors, with a banner, instead of failing on
  every new alert.

### Added
- Operations team on the Agent Development Kit: a `ParallelAgent` of three specialists (maintenance, procurement,
  customer service), each with only its role's tools and a brief in session state, then an operations lead in a
  `SequentialAgent` who reads the briefs and proposes. `mode=team` on the stream endpoint; the plan button, the
  autopilot, and a switch on the Copilot page use it.
- Every trace step carries its author; specialists' briefs show as their own cards.

### Added
- Multimodal Gemini: a structured reader in the gateway (images and PDFs in, schema-checked JSON out; other providers
  refuse clearly).
- Supplier inbox: Gemini reads supplier messages into delivery updates that revise open orders from the moment they
  arrive; three sample messages in `demo/field/inbox` (a delay, a confirmation, a price list).
- Field inspection: Gemini vision reads an inspection photo against the alert's failure mode; findings show on the
  alert and reach the agent through the new `get_field_reports` tool.

### Fixed
- The Streamlit page test used the live proposals file, so a demo approval broke it; `default_services` now takes the
  proposals path and the test passes an empty temporary one.

### Added
- Closed loop: approved proposals become decisions that change stock and queues from their moment on (a transfer leaves
  the sister shelf at once and arrives when promised; covered alerts stop competing for the spare).
- Outcomes settle once the clock passes the real failure or the end of the warning window: hours down with and without
  the plan, and the money saved. They show on the Approvals page and in the live feed with the approval and arrival.
- Approve and reject in the autopilot panel; Reset demo; `GET /api/proposals/outcomes`, `POST /api/proposals/reset`.

### Changed
- The track record scores the analysis without demo approvals, so approving in the app never changes it.

### Added
- Live mode (the Live page): the demo clock runs at 1, 3, or 6 hours per second; a plant event feed streams alerts,
  breakdowns, restorations, and spare orders and receipts; with the autopilot on, every alert that opens a work order
  pauses the clock while Gemini triages it and creates a proposal, then the clock runs on.
- `GET /api/events` and the pure event feed rules; alerts attached to an existing order are marked as covered.

### Added
- Value backtest (`make value`, `GET /api/value`, the Track record page): every alert of the test period analysed as it
  was raised and scored at its real outcome, the copilot against the site acting alone. On the default data: net
  197,949 USD, 662.1 h of downtime avoided, 1,860 USD spent on false alerts.

### Changed
- `create_app` takes the frontend build directory, so tests never depend on a local build.
- Negative money renders as "−$620".

### Added
- React frontend in `src/frontend/` (Vite, TypeScript, Tailwind, Recharts): control room, a copilot page with the
  agent's tool calls streamed live, approvals, and How it works; `make web` with a dev proxy to `make api`.
- The backend serves the built frontend with client-side routes, so one Cloud Run service hosts the whole app.
- Frontend unit tests (Vitest) for formatting and the event-stream parser; `make lint` and `make test` cover both sides.
- The impact endpoint returns the baseline option, so the frontend does not repeat that rule.

### Changed
- The container builds the frontend in a Node stage and serves everything with uvicorn instead of Streamlit.

### Added
- HTTP API (FastAPI, `make api`): health, engine status, scenarios, overview with headline, alert impact and
  evidence, proposals with approval, and the agent run streamed as server-sent events.
- `stream_copilot` yields each agent step as it happens; `run_copilot` is built on it.
- Scenarios and headline summaries now live in the copilot core, shared by the API and the apps.

### Changed
- Python packages live under `src/backend/`, leaving `src/frontend/` for the React app; imports are unchanged.

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
