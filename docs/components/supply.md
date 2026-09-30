<!-- Component reference, imported unchanged from the standalone repository at the version named below. -->

> **Imported from supply-chain-ontology v0.7.2.** In this repository, this package lives in `src/supply_ontology`, its governed files in `semantic/supply/`, its data in `data/supply/`, and its tests in `tests/supply_ontology/`. Make targets and console scripts carry a `supply-` prefix (for example `make supply-data`, `supply-generate-data`). `make data` builds both worlds.

# Supply Chain Ontology and Governed Conversational Analytics

A governed semantic layer for supply chain data: one ontology, one definition per metric, and a natural-language interface that cannot drift from those definitions.
Questions from planning, procurement, and logistics resolve to the same metric id, compile to the same SQL, and return the same number.
Everything runs locally on synthetic data with DuckDB and a local LLM.

## The problem

Supply chain data is scattered across ERP, logistics, supplier, and IoT systems with inconsistent definitions, so the same question yields different answers across teams. "On-time delivery" might be measured against the requested date by one team and the committed date by another, counted by lines here and by units there.

## How it works

1. **Ontology.** Entities, attributes, relationships, and hierarchies are declared once in `semantic/ontology.yaml`. Joins are only allowed along declared relationships, and every pair of entities has at most one join path.
2. **Governed metrics.** Each metric in `semantic/metrics/` fixes its grain, time attribution, aggregation, and filters. Look-alike metrics that teams often confuse are declared separately and cross-referenced, never aliased.
3. **Validated catalog.** Loading the semantic layer builds a catalog only when every reference resolves and every business term maps to exactly one metric.
4. **Conversational layer.** Governed wording in the question fixes the metric deterministically. The local LLM only fills in dimensions, filters, and time from a closed catalog, and a deterministic compiler turns the resulting spec into SQL. The model never writes SQL.

## Metrics

| Metric id | Kind | Definition in one line |
|---|---|---|
| `otd` | canonical | Customer order lines delivered complete by the committed date |
| `otd_vs_request` | variant | Same, against the customer's requested date |
| `supplier_otd` | canonical | PO lines received complete by the supplier's latest promised date |
| `carrier_on_time` | variant | Shipments delivered by the planned delivery date |
| `fill_rate` | canonical | Units on each line's first shipment / units ordered |
| `line_fill_rate` | variant | Lines complete on first shipment / lines |
| `order_fill_rate` | variant | Orders with every line complete on first shipment / orders |
| `days_of_inventory` | canonical | Period-end stock value / average daily COGS over a trailing 90 days |
| `landed_cost_per_unit` | canonical | Goods + allocated freight + duty in USD / units received |
| `purchase_price_per_unit` | variant | Goods only in USD / units received |

Full definitions: `semantic/metrics/*.yaml` and `docs/plan.md` section 3.

## Project layout

```
semantic/                 governed layer: ontology.yaml, metrics/*.yaml, dimensions, ambiguous terms, personas
evaluation/questions.yaml persona questions with their expected outcomes, scored by `make eval`
src/supply_ontology/
  core/                   pure: models, parsers, validators, join paths, catalog, query spec, SQL compiler,
                          vocabulary, term binding, grounding, prompts, reply parsing, evaluation scoring
  data_pipeline/          adapters: semantic file loading, DuckDB views, locked raw-source database, local LLM client
    synthetic/            seeded world simulation and source-system renderers
    conform/              sources -> canonical entities, including derived attributes
  services/               query service (spec -> SQL -> result with provenance), NL service, evaluation,
                          consistency demo; settings
  api/                    entry points: query-metric, eval-nl, and consistency-demo CLIs
  ui/                     Streamlit app: ask, demo replay, metric catalog; pure presenters
tests/core/               pure unit tests for the semantic layer
tests/synthetic/          generator invariants, source round trips, stories, determinism
tests/conform/            conform reconstructs the truth; derived attribute definitions; loud failures
tests/compiler/           golden values for every metric on a hand-built world; compiler guarantees
tests/nl/                 vocabulary rules, term binding, grounding, prompts, reply parsing, eval scoring
tests/services/           query and NL services on the conformed small world (NL with a scripted stub model)
tests/ui/                 presenters, and the real page run headless with injected services
tools/check_code_rules.py file length, function length, and summary docstring rules (run by `make lint`)
tests/integration/        tests that read files: semantic layer, ontology contract, writer
docs/plan.md              design plan and milestones
data/                     generated locally by `make data`; never committed
```

## Setup

```bash
make setup    # creates .venv and installs the package with dev tools
make data     # generates the synthetic dataset into data/ (about 10 seconds)
make conform  # conforms data/sources into data/conformed (about 4 seconds)
make test     # runs the test suite
make lint     # runs ruff and the code rule checks
make eval     # scores the NL layer against the live local model (see Local LLM)
make demo     # runs the consistency demo against the live local model
make demo-offline  # team recipes vs the governed answer; no model needed
make ui       # opens the Streamlit UI
```

Requires Python 3.10 or later. No cloud services, credentials, or network access are needed after installation.

## Synthetic data

`make data` (or `generate-data --seed N --out DIR`) simulates two years of a fictional four-plant business. It first builds one consistent world, then renders it as deliberately inconsistent source systems.

| Folder | Contents |
|---|---|
| `data/sources/erp/` | Vendor, item, customer, plant, and contract masters (xlsx); purchase orders, receipts, sales orders, weekly inventory (Parquet) |
| `data/sources/tms/` | Shipments and outbound shipment lines with partner codes, UTC timestamps, and case quantities |
| `data/sources/supplier_portal/` | Delivery confirmations and revisions |
| `data/sources/treasury/`, `trade/`, `mdm/` | FX rates per USD, duty percentages, partner crosswalk |
| `data/truth/` | Canonical entity tables, used only to test the conform pipeline |
| `data/manifest.json` | Seed, config, planted-story facts, and a content fingerprint per file |

Four stories are planted so the demo questions have real answers:
- a major supplier's on-time delivery degrades over one quarter
- a freight spike hits one inbound lane
- one plant overstocks bearings
- aftermarket customers request dates shorter than transit allows

Details are in `docs/plan.md` section 4. The same seed always produces the same data.

## Conformed layer

`make conform` resolves every source trap and writes one Parquet file per ontology entity to `data/conformed/`, including all derived attributes (completion dates, on-time flags, landed cost, trailing COGS). The days-of-inventory window is read from the metric definition, not hard-coded. `DuckDBConnectionManager` exposes each entity as a view for querying. The conform output reproduces the truth tables exactly, and the test suite checks this for every entity.

## Querying governed metrics

A query spec names metrics from the catalog, optional `entity.attribute` dimensions and filters, a time range, and a time grain. The compiler validates it and produces one parameterised SQL statement:

```bash
query-metric '{"metrics": ["supplier_otd"], "dimensions": ["supplier.supplier_id"], "time_grain": "quarter",
               "filters": [{"dimension": "supplier.supplier_id", "operator": "equals", "value": "V10001"}]}' --show-sql
```

The compiler applies these rules, and the golden tests check each one on a hand-built world:
- **No double counting:** each metric aggregates at its own grain and joins only upward along the declared paths.
- **Own time attribution:** each metric's own time dimension decides its period. Rows attributed after the data's as-of date (the last inventory snapshot) are excluded, because their outcome is not known yet.
- **Period-end metrics:** days of inventory takes the last snapshot in each period.
- **Ratios:** divide with `NULLIF`, so zero demand reads as no value instead of an error.
- **Parameters:** all values are bound, so the same spec always yields byte-identical SQL and the same fingerprint.

## Ground rules

- **Synthetic data only.** Every dataset comes from a seeded generator in this repo. No real client or employer data, schemas, or names are used.
- **Fully local.** DuckDB over Parquet and `.xlsx`; no cloud warehouse and no cloud LLM API.
- **Portable.** `data/` is not committed; the generator recreates the identical dataset on any machine from its seed.

## Asking questions

`NLService.ask(question, persona)` returns one of three outcomes:
- **Answer:** the query result with its SQL, fingerprint, metric definitions, and whether the metric was fixed by the wording or chosen by the model.
- **Clarification:** the wording could mean several governed metrics (for example "how are we doing on time?"), so the user picks one.
- **Unanswerable:** no governed metric answers the question, or the model could not produce a valid spec after one retry.

How a question is resolved:
- **Metric:** the longest governed phrase in the question binds the metric, including the persona's jargon. The model cannot change it.
- **Ambiguous phrases:** a phrase listed in `semantic/ambiguity.yaml` is settled only by context words for exactly one candidate. Otherwise the service asks.
- **Time and dimensions:** these come from the question's words. "Last quarter" is a named range computed from the data's as-of date, so every persona gets the same dates.
- **Checks:** the model's spec must pass compiler validation and governance checks, which allow only governed dimensions and filter values that exist in the data.

Because of these rules, planning's "service level", procurement's "customer delivery performance", and logistics' "customer on time delivery rate" all compile to the same SQL fingerprint.

## Consistency demo

`make demo` (or `consistency-demo --model NAME`) runs `docs/plan.md` section 6 against the local model:
0. **The problem, reproduced without a model.** Each team's own SQL recipe (`demo/team_recipes.yaml`) runs on the raw sources next to the governed answer. `make demo-offline` prints this part alone:

   | Team | Recipe's choice | Last quarter (2026 Q2, default seed) |
   |---|---|---|
   | Planning | requested date instead of committed date (effectively `otd_vs_request`) | 58.6% |
   | Procurement | ship date instead of delivery date; keeps cancelled lines | 90.6% |
   | Logistics | shipments against the carrier's plan (effectively `carrier_on_time`) | 85.7% |
   | Governed `otd` | committed date, delivered complete, non-cancelled lines | 76.8% |

1. **The problem.** Each persona's phrasing of customer on-time delivery goes through naive text-to-SQL. The model sees the raw source tables and writes its own query, so each team's answer depends on the columns it happens to choose.
2. **The fix.** The same three phrasings go through the governed layer. They should resolve to `otd`, share one SQL fingerprint, and return one number.
3. **The boundary.** "Were we on time for suppliers last quarter?" resolves to `supplier_otd`, a different declared metric.

The naive SQL runs on a DuckDB connection that is locked against file and network access, with a time limit and a row cap. Each run is saved to `data/demo/<model>.json`.

First live run (2026-09-29, Qwen3.6-35B-A3B 4-bit):

| Team | Naive text-to-SQL | What the model's query did | Governed |
|---|---|---|---|
| Planning | 64.9% | Q3 2026 (still in progress); shipped quantity covers the order, with no dates and case quantities added to units | 76.8% |
| Procurement | 73.8% | Q3 2026 by pickup date; carrier on-time, with shipments still in transit counted late | 76.8% |
| Logistics | 85.6% | Q3 2026 by delivery date; carrier on-time | 76.8% |

All three governed answers used the same SQL (fingerprint `67ca8d67921d`), and the supplier question resolved to `supplier_otd` (84.1%).

## User interface

`make ui` opens a Streamlit app with three tabs:
- **Ask:** choose a team and ask a question. The answer shows the value, whether the wording or the model chose the metric, the period, the as-of date, the metric's full definition, and the SQL with its fingerprint. When a question is ambiguous, the app offers the candidate metrics as buttons.
- **Consistency demo:** the team recipes next to the governed answer, computed from the raw sources with no model, and replays of runs saved by `make demo`.
- **Metric catalog:** every governed metric with its synonyms, look-alikes, and definition, plus the selected team's own phrases.

The page loads without contacting the model. Only asking a question sends a request.

## Local LLM

The conversational layer calls an OpenAI-compatible endpoint served by `mlx_lm.server`:

```bash
mlx_lm.server --model ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-6Bit --port 8080
```

Model and endpoint are set per machine in `.env`, copied from `.env.example`. The Makefile loads it for every target, and `make settings` prints the endpoint and model a live command will use. `LLM_MODEL` must be the model the server on that port serves: asking for any other model makes the server load it in place of that one. `make eval` (or `eval-nl --base-url URL --model NAME`) runs the 24 questions in `evaluation/questions.yaml` and writes a report per model to `data/eval/`. The unit tests use a scripted stub model and never need a server.

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| 1 | Ontology and metric YAML with a validating catalog | Done |
| 2 | Seeded synthetic source generator with planted stories | Done |
| 3 | Conform pipeline to entity Parquet and DuckDB views | Done |
| 4 | Query spec to SQL compiler with golden tests | Done |
| 5 | Natural-language service on the local model | Done |
| 6 | Consistency demo across personas | Done |
| 7 | Streamlit UI | Done |

## Known issues

Open items and the next steps are tracked in `techdebt.md`.

## Branching and releases

Git Flow: features branch from `develop` and merge back by PR; each milestone ships as a `release/X.Y.Z` branch merged into `main`, tagged `vX.Y.Z`, and published as a GitHub release. See `CHANGELOG.md` for what changed in each version.
