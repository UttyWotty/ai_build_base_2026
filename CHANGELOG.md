# Changelog

This file records every notable change to the project, newest first, in Keep a Changelog format.
Work in progress collects under Unreleased and moves to a dated version section when a release branch is cut.
Versions follow semantic versioning; before 1.0 each milestone is a minor release.

## [Unreleased]

### Added
- `llm_gateway` package: one `LLMClient` interface with a Gemini adapter (google-genai, AI Studio key or Vertex AI) and
  the OpenAI-compatible local adapter. `LLM_PROVIDER` chooses between them.
- The Gemini adapter retries rate limits and server errors with capped exponential backoff, and reports an empty reply
  with its finish reason.
- `--provider`, `--model`, and `--base-url` on every command that calls a model; evaluation reports record the provider.

### Changed
- Both component packages build their model client through the gateway; their own model settings are gone.

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
