<!-- Component reference, imported unchanged from the standalone repository at the version named below. -->

> **Imported from pdm-oee-command-center v0.8.3.** In this repository, this package lives in `src/pdm_oee`, its governed files in `semantic/pdm/`, its data in `data/pdm/`, and its tests in `tests/pdm_oee/`. Make targets and console scripts carry a `pdm-` prefix (for example `make pdm-data`, `pdm-generate-data`). `make data` builds both worlds.

# Predictive Maintenance and OEE Command Center

Converges synthetic OT sensor streams with ERP and maintenance records to predict equipment failures, automate work orders, and lift Overall Equipment Effectiveness.

## Problem

Unplanned downtime costs manufacturers because OT sensor data (vibration, temperature, RPM) sits apart from ERP and maintenance context. This project correlates the two, predicts failures in advance, supports root-cause investigation in natural language, and delivers a command-center experience for alert triage and action.

## Ground rules

- **Synthetic data only.** Every dataset is produced by a seeded generator in this repo. No real client or employer data, schemas, or names are ever used.
- **Fully local.** DuckDB queries Parquet files (high-volume data) and `.xlsx` files (small ERP-style exports). There is no cloud warehouse and no cloud LLM API.
- **Portable.** `data/` is not committed; the generator recreates the identical dataset on any machine from its seed.

## Local LLM

The natural-language layer calls an OpenAI-compatible endpoint served by `mlx_lm.server`:

```bash
mlx_lm.server --model ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-6Bit --port 8080
```

Model and endpoint are set per machine in `.env`, copied from `.env.example`. The Makefile loads it for every target, and `make settings` prints the endpoint and model a live command will use. `LLM_MODEL` must be the model the server on that port serves: asking for any other model makes the server load it in place of that one.

## Governed catalog

`semantic/` holds everything the project treats as a definition, and loading it builds a catalog only when every check passes:

| File | Contents |
|---|---|
| `plant.yaml` | Sensor types, and asset classes (CNC machining centre, hydraulic press, conveyor drive) with components, sensors and healthy ranges, and failure modes with symptom sensors, P-F interval, repair time, and recommended action |
| `losses.yaml` | Seven losses, each with its OEE factor and source; planned stop reasons; and the stop reasons booked to each availability loss |
| `measures.yaml` | Every base quantity (planned production time, run time, valuable operating time, and more), each with one grain, unit, and definition |
| `metrics/*.yaml` | Ten metrics, each a ratio of two measures: `availability`, `performance`, `quality`, `oee`, `mtbf`, `mttr`, `pm_compliance`, and the declared look-alikes `teep`, `oee_nameplate`, `availability_incl_small_stops` |

The checks include:
- every sensor, component, and symptom reference resolves
- every component has a failure mode, and failure mode ids are unique across classes
- each loss's source fixes its factor
- a percent metric divides like units, and an hours metric divides hours by a count
- every business term resolves to one metric
- look-alike declarations are mutual

## Synthetic plant

`make data` (or `generate-data --seed N --out DIR`) simulates one year of a fictional two-site plant in about 8 seconds:
- **Scale:** 24 assets, 84 sensors, and 1,530 shifts, with about 110 predictable failures and 180 tool changer jams.
- **Simulation:** one consistent plant is simulated minute by minute first, then rendered as five messy source systems.

| Folder | Contents |
|---|---|
| `data/sources/asset_register/` | Assets with their CMMS numbers and MES workcenters; sensors with historian tag paths and units |
| `data/sources/historian/` | 4.4 million 10-minute readings by tag path, in UTC, with site units and quality codes |
| `data/sources/mes/` | State intervals and cumulative counters in local time, site reason codes, the shift calendar |
| `data/sources/erp/` | Products, routings (parts per hour at US1, seconds per part at DE1), production orders |
| `data/sources/cmms/` | Corrective, preventive, and instrument work orders, with blank codes, duplicates, and late closures |
| `data/truth/` | Canonical tables, used only to test the conform pipeline |
| `data/manifest.json` | Seed, configuration, measured story facts, and a fingerprint per file |

Six stories are planted, and the manifest records what each one looks like in the data:
- a spindle bearing failure with six days of warning
- hydraulic pump wear over three weeks
- a sensor swap with a calibration offset and no failure behind it
- a line with preventive maintenance twice as often and no fewer failures
- scrap rising with summer coolant temperature on one line
- a conveyor with frequent stops under five minutes

## Conformed layer

`make conform` turns the five source systems into one Parquet file per canonical entity under `data/conformed/`, in about 6 seconds, and `DuckDBConnectionManager` exposes each as a view.

The conform step knows the sources only through `semantic/source_mappings.yaml`:
- **Per site:** number, time zone, and the quality, state, and reason codes.
- **Printed units:** each unit string with its conversion to canonical units.
- **CMMS:** work-type codes, failure codes, and keywords for failure codes left blank.

Its rules:
- **Ids:** asset numbers encode site, line, and position; tags and measurements map through the register; equipment types and sensors map through the catalog's labels.
- **Time:** local times convert to UTC per site. MES rows are taken in sequence, so the repeated hour when daylight saving ends reads correctly.
- **Counts:** a shift's count is the counter's rise, or the reading itself after a reset; the go-live snapshot is the baseline.
- **Failures:** each corrective order belongs to the breakdown that was open when it was created, and the earliest order per breakdown is the real one. Failure times come from the breakdown, not the order's closure date.
- **Loud failures:** anything the mappings do not declare (a tag, code, unit, or failure text) raises `ConformError`.

Every conformed table matches its truth table value for value, on the full year and in the test suite.

## OEE engine

`make oee` (or `oee-report --by line_id --start 2026-06-01 --end 2026-07-01`) prints availability, performance, quality, and OEE for a grouping, plus the loss waterfall. `OEEService` answers the same questions for the later milestones.
- **Measures:** every measure in `measures.yaml` is computed per asset and shift from the conformed state intervals, split at shift boundaries. A stop is small when its whole recorded duration is under five minutes, even if it crosses a shift boundary.
- **Rollups:** any metric is sum(numerator) / sum(denominator), by asset, line, site, asset class, shift date, week, or month. Ratios are never averaged, and a zero denominator gives no value.
- **Waterfall:** planned production time minus the seven losses equals valuable operating time. Reduced speed is the residual after small stops, so the waterfall always reconciles.
- **Reliability:** MTBF, MTTR, and preventive-maintenance compliance follow their measure definitions for any period.
- **Performance above 100%** is reported as an anomaly (a wrong ideal cycle time), never capped.

On the default year, plant OEE is 82.7%. US1-L1's performance is about four points below the other lines, which is the small-stop conveyor story.

## Failure prediction

`make predict` (or `predict-failures`) runs the backtest in about 15 seconds and saves the classifier, its threshold, and the report to `data/models/`.
- **The panel:** one row per asset, predictable failure mode, and operating hour, with rolling 24-hour and 7-day features. The features use each symptom sensor's running readings, normalised to the sensor's own post-repair baseline.
- **Labels:** a row is positive when that mode fails within 7 days. Hours while the asset is down, inside an unfinished baseline window, or in the censored last week are not scored.
- **Two predictors:** a health-index baseline (the worst symptom over the last day) and a scikit-learn gradient-boosted classifier.
- **Scoring:** event by event. A failure counts as caught when an alert starts between 7 days and 24 hours before it. Thresholds are chosen on a separate validation block for at most one false alert per asset per month.

Test results, last four months of the default year:

| Predictor | Failures caught | False alerts per asset-month | Median lead |
|---|---|---|---|
| Gradient-boosted classifier | 27 of 41 (65.9%) | 0.16 | 86 h |
| Health-index baseline | 26 of 41 (63.4%) | 0.46 | 73 h |

The planted bearing failure is caught 32 hours ahead and the hydraulic pump 153 hours ahead. The calibration swap raises no alert.

## Alerts and draft work orders

`make alerts` (or `replay-alerts`) replays the classifier's alerts over the test period:
- **Drafts:** each alert becomes a draft work order with evidence in engineering units, a repair deadline (half the P-F interval), a planned slot or an unplanned stop, a priority, and the recommended action.
- **Dedup:** alerts arriving while a draft, open order, or due preventive task already covers them are attached to it instead.
- **Outbox:** drafts go to a simulated CMMS outbox (`data/outbox/work_order_drafts.json`), where they wait for approval. The full replay with each alert's backtest truth goes to `data/alerts/replay.json`.

On the default year's last four months:
- **Alerts:** 49, of which 29 were useful, 5 late, and 15 false.
- **Handling:** 38 new drafts, 8 attached to due preventive tasks, and 3 attached to earlier alerts; 19 found a planned slot.
- **Lift estimate:** OEE from 82.27% to 82.50% and availability from 92.42% to 92.68%, from 128 h of recovered breakdown time less 8 h of inspections. The gain is small because breakdowns are only about 1% of planned time in this plant; the assumptions are printed with the number.

## Natural-language investigation

`make ask Q="Why did quality drop on line DE1-L2 in summer 2026?"` has the local model investigate with governed tools:
- **Tools:** OEE summary and trend, loss breakdown and top contributors, sensor trend, failures, work orders, alerts, and quality drivers.
- **No SQL:** the model never writes SQL or computes a metric. It calls tools, sees their results, and answers.
- **Number check:** every number in the answer must match a tool result, or the answer is retried once and then marked unverified.
- **Evaluation:** `make investigate-eval` scores the ten questions in `evaluation/investigation.yaml` and writes a report to `data/eval/`.

On the default data, the tools surface each story:
- `top_loss_contributors` puts conveyor US1-L1-04 first for small stops with 274 hours.
- `quality_drivers` finds coolant temperature correlating with DE1-L2's weekly quality at -0.84.
- `sensor_trend` shows the story bearing's vibration climbing from 1.5 to 3.5 mm/s before its July failure.

Both commands need an OpenAI-compatible server at `LLM_BASE_URL`. **Live evaluation:** 10 of 10 on Qwen3.6-35B-A3B 4-bit (about 2 minutes) and 10 of 10 on Qwen3.8-27B 6-bit.

## Command center

`make ui` opens the Streamlit command center:
- **Alert queue:** draft work orders from the outbox, most urgent first. Each shows its evidence in engineering units against the healthy range, the repair deadline, the planned slot or unplanned stop, and the recommended action, with approve and dismiss buttons that only change the draft's status.
- **Asset health:** every sensor's daily running mean against its healthy range, plus the asset's failures, work orders, and alerts, through the same tools the language model uses.
- **OEE and losses:** the governed metrics by any grouping and period, and the loss waterfall.
- **Ask:** a question for the local model, answered through governed tools. It shows whether every number was traced to a tool, and each tool call can be inspected.
- **Prediction model:** the backtest for the classifier and the baseline, and the OEE lift with its assumptions.

The page reads the conformed data and the files `make predict` and `make alerts` write. It contacts the model only when a question is asked.

## Project layout

```
semantic/                 governed catalog: plant, losses, measures, metrics, source mappings
src/pdm_oee/
  core/                   pure: catalog models, parsers, validators; shift measures, loss waterfall, rollups, reliability;
                          sensor baselines, feature panel, event-level alert scoring, work-order rules, lift replay;
                          investigation tool catalog, reply protocol, number check, evaluation scoring
  services/               OEE service; prediction backtest and models; alert replay; investigation tools and loop; settings
  api/                    entry points: oee-report, predict-failures, replay-alerts, and investigate CLIs
  ui/                     Streamlit command center: five tabs; pure presenters
  data_pipeline/          adapters: catalog file loading, DuckDB views, model store, CMMS outbox, alert replay, LLM client
    synthetic/            seeded plant simulation and source-system renderers
    conform/              sources -> canonical tables (pure transforms; reader and store are the only I/O)
tests/core/               pure unit tests for every parser and validator
tests/integration/        the checked-in catalog, and YAML loading errors
tests/synthetic/          generator determinism and invariants, planted stories, every source trap's round trip
tests/conform/            conformed tables equal the truth; loud failures; daylight-saving handling
tests/oee/                golden values on a hand-built plant; identities and stories on the small plant
tests/prediction/         alert scoring by hand, no look-ahead, labels, re-baselining, the backtest and model store
tests/alerts/             work-order rules and lift arithmetic by hand, the outbox, the replay on the small plant
tests/investigation/      tool validation, reply parsing, number checks, scoring, and the loop with a scripted model
tests/ui/                 presenters, and the real page run headless with injected services and a scripted model
evaluation/               investigation questions with expected tools and findings
tools/check_code_rules.py file length, function length, and summary docstring rules (run by `make lint`)
docs/plan.md              design plan and milestones
```

## Setup

```bash
make setup    # creates .venv and installs the package with dev tools
make data     # generates the synthetic plant into data/ (about 8 seconds)
make conform  # conforms data/sources into data/conformed (about 6 seconds)
make oee      # prints OEE by line and the loss waterfall for the last four weeks
make predict  # runs the failure prediction backtest and saves the model (about 15 seconds)
make alerts   # replays the test period as alerts and draft work orders, with the OEE lift
make ask Q="..."        # investigates one question with the local model
make investigate-eval   # scores the evaluation questions against the local model
make ui       # opens the command center
make test     # runs the test suite
make lint     # runs ruff and the code rule checks
```

Requires Python 3.10 or later.

## Roadmap

The design, metric definitions, and decisions are in `docs/plan.md`.

| Milestone | Scope | Status |
|---|---|---|
| 1 | Plant model and metric catalog with a validating loader | Done |
| 2 | Synthetic plant generator with degradation and planted stories | Done |
| 3 | Conform pipeline to canonical tables and DuckDB views | Done |
| 4 | OEE engine and loss waterfall with golden tests | Done |
| 5 | Failure prediction with an event-level backtest | Done |
| 6 | Alerts, draft work orders, and the OEE lift estimate | Done |
| 7 | Natural-language investigation on the local model | Done |
| 8 | Streamlit command center | Done |

## Known issues

Open items and the next steps are tracked in `techdebt.md`.

## Branching and releases

Git Flow: features branch from `develop` and merge back by PR; each milestone ships as a `release/X.Y.Z` branch merged into `main`, tagged `vX.Y.Z`, and published as a GitHub release. See `CHANGELOG.md` for what changed in each version.
