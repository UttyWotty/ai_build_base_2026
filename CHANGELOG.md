# Changelog

This file records every notable change to the project, newest first, in Keep a Changelog format.
Work in progress collects under Unreleased and moves to a dated version section when a release branch is cut.
Versions follow semantic versioning; before 1.0 each milestone is a minor release.

## [Unreleased]

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
