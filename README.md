# OSI (Opsight Intelligence)

At 2 a.m., two machines need the last spare part. OSI decides who gets it, covers the other, and proves it paid off.

An AI operations copilot for manufacturing. Predicting a failure is the easy part; OSI traces each alert through spare parts, suppliers, and customer orders, a team of Gemini agents drafts the plan, and a person approves it.
Built for the AI Builder Cup 2026, Manufacturing track (Intelligent Operations and Industrial Efficiency).

**Try it live:** https://ops-copilot-432875717420.asia-southeast1.run.app (Cloud Run in Singapore, Gemini on Vertex AI). The bearing scenario at 02:00 on 25 July is the default clock; open **Control room**, pick US1-L2-01, and press **Draft the plan with the copilot**.

**Video:** to be added. **Deck:** [`docs/OSI-deck.pdf`](docs/OSI-deck.pdf).

| | |
|---|---|
| **Track record** | 38 alerts over four months, scored against what really happened: **662 hours** of downtime avoided and **$197,949 net saved**, after charging the plan for its spend on false alerts (`make value`) |
| **Agent evaluation** | **8/8** scenarios with Gemini 3.8 Flash on Vertex AI (`make eval`) |
| **Built with** | Gemini on Vertex AI, Google Agent Development Kit, Cloud Run, React, FastAPI |

## The problem

When a machine is about to fail, maintenance, stores, purchasing, and customer service each see one piece of the problem in their own system. The question that matters ("this spindle fails in about a day; do we have the bearing, and whose orders slip if we don't?") takes hours of calls to answer, while the warning window runs out. Predictive maintenance tools stop at the alert; the expensive mistakes happen between departments.

## What it does

A sense, reason, act loop over governed operational data from a plant and its supply network:
1. **Sense.** A gradient-boosted model scores every asset from its sensors. It caught 27 of 41 failures at 0.16 false alerts per asset-month, with a median warning of 86 hours.
2. **Reason.** A team of Gemini agents on Google's Agent Development Kit investigates, using governed tools only. The maintenance, procurement, and customer specialists work in parallel, and an operations lead weighs their briefs.
3. **Act.** The lead proposes the work order, the parts action, and the customer note. A person approves, and the approval changes the world: stock moves, conflicts clear, and the outcome shows once the clock passes it.

What makes it trustworthy:
- **No invented numbers.** Every number in an answer is checked against the tool results before it is marked verified.
- **No SQL from the model.** Supplier metrics compile from governed definitions, with a SQL fingerprint.
- **No peeking at the future.** Every tool answers as of the demo clock; outcomes count only once they are in the past.
- **No silent actions.** Agents propose; only people approve.
- **No runaway runs.** A run stops after 25 model calls (50 for the team), far above the 5 to 20 a normal run needs.
- **Feedback flags, never silences.** An operator can mark an alert as false. Later alerts on the same machine and failure mode carry the note and ask for an inspection first, but stay visible: in the data, two machines with an earlier false alert failed for real weeks later.

## Status

| Version | Milestone | Status |
|---|---|---|
| 0.1.0 | Monorepo foundation | Released |
| 0.2.0 to 0.7.0 | Model layer, bridge and impact, operations agent, web app, Cloud Run kit, submission kit | Released as 0.7.0 |
| 0.8.0 | React and FastAPI; track record; live mode and autopilot; closed loop; multimodal Gemini; multi-agent team; model fallback | Released |
| 0.8.1 | The OSI name; CI; architecture page with the challenge check | Released |
| 0.8.2 | Inspection photos checked by Gemini; road to submission | Released |
| 0.9.0 | Live on Cloud Run with Gemini on Vertex AI; 8/8 evaluation; submission write-up around the judging criteria | Released |
| 0.10.0 | Ask about this on the field inspection; operator verdicts on false alerts | Released |
| 0.10.1 | Story opens on scarcity; deck PDF in docs | Released |
| 0.10.2 | Streamlit app removed; challenge check current | Released |
| 0.11.0 | Usage limit on Gemini calls (10 per visitor, 60 in total per hour) | Released |
| 0.11.1 | One instance at most; deployed with the usage limit | Released |
| 0.11.2 | UI polish: loading screen, full story line, How it works title | Released |
| 0.11.3 | Fix: no guessed alert ids; every run capped | Released |

Open items, in priority order, are in `techdebt.md`: the road to submission, starting with the video and the write-up.

## Quick start

Requires Python 3.11 and Node.js 20 or later.

```bash
cp .env.example .env   # then add GEMINI_API_KEY (free at aistudio.google.com)
make setup             # backend venv with dev tools, and the frontend packages
make data              # both synthetic worlds and the bridge (about 30 seconds)
make models            # the failure model and its alert replay (about 20 seconds)
make api               # terminal 1: the backend on port 8000
make web               # terminal 2: the app on http://localhost:5173
```

Other commands:

| Command | What it does |
|---|---|
| `make test`, `make lint` | Backend and frontend tests; ruff, code rules, TypeScript check, and lint |
| `make value` | The track record in the terminal |
| `make impact A=<alert> [AS_OF=...]` | One alert's impact analysis |
| `make ask Q="..." [AS_OF=...]` | One question to the agent, with its trace |
| `make eval` | The agent's eight evaluation scenarios against the configured model |
| `make image`, `make deploy` | Build and run the container locally; deploy to Cloud Run (`docs/HANDOVER.md`) |
| `make settings` | The model and data directories in effect |

CI (`.github/workflows/ci.yml`) runs `make setup`, `make lint`, and `make test` on Python 3.11 and Node 22. To save Actions minutes it is started by hand from the Actions tab (Run workflow) before a merge or release; the local gate stays `make lint` and `make test`.

## The app

The top bar sets the demo clock, either a named scenario or any time in the data. Every page answers as of that moment.

| Page | What it shows |
|---|---|
| **Live** | The plant replayed as it happens: the clock runs at 1, 3, or 6 hours per second, and alerts, breakdowns, restorations, and spare orders and receipts stream in. With **Autopilot** on, each new alert pauses the clock while the agent team triages it and leaves a proposal, with approve and reject in place. On quota or credential errors the autopilot stops itself and explains why. |
| **Control room** | Headline numbers, the open alerts, and for the selected one: the spare conflict, stock at both sites, the supplier's governed on-time delivery, every priced option, the sensor evidence against its normal band, field inspections with **Ask about this** for follow-up questions to the copilot, the operator's verdict (mark an alert as false, with a reason), and the customers at risk. **Draft the plan with the copilot** streams the team's work live. |
| **Copilot** | Free questions to one agent or to the team, with the live tool timeline, each specialist's brief, the answer, and the verified badge. |
| **Supplier inbox** | Gemini reads suppliers' messages (text or PDF) into delivery updates. A new date revises the open order from the moment the message arrived. |
| **Approvals** | Proposals to approve or reject. An approved plan moves stock and clears conflicts from its moment on, and its outcome shows once the clock passes the failure, for example "down 26.0 h with the plan instead of 230.3 h, $100,077 saved". **Reset demo** clears the queue. |
| **Track record** | Every alert of the test period scored at its real outcome: the plan against the site acting alone. |
| **How it works** | The pitch, the loop, the architecture, the guardrails (including operator verdicts), and the Google Cloud setup with its protections. |

## Agents

**The operations team** (`src/backend/copilot/services/agent_team.py`) plans and triages:
- An ADK `ParallelAgent` runs three specialists at once, each with only its role's tools and a brief in session state. The maintenance planner has sensor evidence, field reports, and history. The procurement lead has spares, options, and supplier records. The customer service lead has orders at risk and drafts the customer note. Each can list the open alerts and is told never to guess an alert id.
- An ADK `SequentialAgent` then runs the operations lead, whose instruction reads the three briefs. It balances urgency, cost, and customer exposure, and calls `propose_action_plan`.

**The single agent** answers free questions with all tools. Both run on `stream_copilot`, which streams every tool call, result, and brief with its author.

| Tool | Returns |
|---|---|
| `list_open_alerts` | Alerts waiting for a repair, earliest deadline first |
| `analyse_alert_impact` | Spares at both sites, the alert queue, supplier record, every priced option, worst case, customers at risk |
| `get_sensor_evidence` | Daily means of the failure mode's symptom sensors over 7 days, with normal ranges |
| `get_field_reports` | Inspection photo findings and supplier delivery updates that Gemini has read, and operators' verdicts on this alert and earlier alerts of the same asset and failure mode |
| `get_supplier_record` | Governed `supplier_otd` with its SQL fingerprint, and the expected lateness |
| `oee_summary`, `failures`, `work_order_history` | Plant history from the OEE engine |
| `propose_action_plan` | A proposal for a person to approve; its numbers come from the analysis, not the model |

**Evaluation.** `make eval` runs eight scenarios (`evaluation/copilot/scenarios.yaml`) and checks the tools called, required facts, the number check, and the proposal:
- **Local Qwen3.6-35B-A3B:** 7 of 8. The miss was a tool gap, now fixed.
- **Gemini:** **8/8** with `gemini-3.8-flash` on Vertex AI (2026-10-12).

## Models

Every language feature goes through `src/backend/llm_gateway`:
- **`LLM_PROVIDER=gemini`** (default) uses the google-genai SDK. It reads `GEMINI_API_KEY` locally, or Vertex AI through the service account on Google Cloud. `GEMINI_MODEL` defaults to `gemini-3.8-flash`.
- **`GEMINI_FALLBACK_MODELS`** lists backup models, tried in order when one is out of quota or unavailable. Each Gemini model has its own free-tier quota, and the trace notes each switch.
- **Errors in plain words.** People see "quota used up", "Gemini overloaded", "credentials refused", or "model not available", each with what to do; the raw text sits behind a details toggle.
- **Multimodal reading** (`multimodal.py`) turns images and PDFs into JSON that follows a schema. Only Gemini reads them; other providers refuse clearly.
- **`LLM_PROVIDER=local`** uses an OpenAI-compatible server (`LLM_BASE_URL`, `LLM_MODEL`) as the offline fallback for text.

## How the numbers are made

- **Two synthetic worlds.** A two-site plant (sensors, MES, CMMS, ERP) and a four-plant supply network (ERP, TMS, supplier portal, treasury), each generated from a seed. Both end on 2026-09-28. The component references are `docs/components/pdm.md` and `docs/components/supply.md`.
- **The bridge** (`semantic/bridge/bridge.yaml`) links sites to supply plants, components to spares and suppliers, and lines to the customer parts they make. `make bridge` simulates each site's spares store from the plant's repairs, with orders arriving as late as each supplier really delivers in the supply world.
- **The impact analysis** prices every way to get the spare (own stock, open order, air transfer, broker, new order) as extra spend plus lost contribution. It adds the customer lines due during the outage and a worst case learned only from past alerts.
- **The track record** (`make value`) prices the plan and the site's own choice at each alert's real outcome:

| Alerts scored | Plans that differed | Downtime avoided | Saved on failures | Spent on false alerts | Net |
|---|---|---|---|---|---|
| 38 (26 real failures, 12 false) | 6 | 662.1 h | $199,809 | $1,860 | **$197,949** |

The demo moment comes from the data, with nothing planted on top. At 02:00 on 25 July 2026, two spindle-bearing alerts at US1 need the one bearing set on the shelf. The replacement is with supplier V10001, which was on time for 66.1% of its lines over 90 days. The copilot gives the set to the overdue alert and covers the other with an air transfer from DE1 for $650. Waiting instead would mean 190 hours down and four customer lines at risk.

## Connecting a real plant

The data here is synthetic, generated from seeds and shaped like the systems a plant already runs. A real plant feeds the same governed layer:

| The plant's system | What OSI takes from it | What the agents can answer |
|---|---|---|
| Sensor historian | Sensor history and live readings | Which machine fails, and when |
| Maintenance system (CMMS) | Work orders and repairs | What fixed it last time |
| ERP: stores and purchasing | Stock, open orders, supplier deliveries | Is the part here, or when will it arrive |
| ERP: order book | Customer orders per line | Which customers are at risk |
| Inbox and shop floor | Supplier messages, inspection photos | Did the date move, and is the wear real |

The agents only see governed tools, so connecting a plant means mapping its data and adding its entries to the bridge (`semantic/bridge/bridge.yaml`), not rewriting prompts.

## Project layout

```
src/backend/pdm_oee/          plant: simulation, conform, OEE, failure prediction, alerts
src/backend/supply_ontology/  supply: simulation, conform, ontology, metric compiler, governed questions
src/backend/llm_gateway/      model gateway: Gemini (text and multimodal) or a local model, retries, fallback
src/backend/copilot/          bridge, impact, track record, decisions, field inputs, agents, FastAPI
src/frontend/                 React app (Vite, TypeScript, Tailwind, Recharts)
semantic/                     governed definitions: pdm/, supply/, bridge/
evaluation/, demo/            evaluation sets; demo recipes and field samples (demo/field)
tests/                        tests per package (pytest); the frontend's tests sit next to its code (Vitest)
docs/                         plan, submission write-up, deck (PDF), demo script, handover, architecture page, component references
Dockerfile, deploy/           one container and the Cloud Run deploy script
data/                         generated by make data and make models; never committed
```

Layers import downward only: `api` -> `services` -> `data_pipeline` -> `core`. The copilot builds on the two component packages, never the reverse.

## HTTP API

| Endpoint | Returns |
|---|---|
| `GET /health`, `GET /api/engine-status` | Liveness (no data or model access); readiness and the model in use |
| `GET /api/scenarios`, `GET /api/overview?as_of=` | Demo moments; open alerts with recommendations and the headline |
| `GET /api/alerts/{id}/impact?as_of=`, `.../evidence` | One alert's impact analysis (with the baseline option) and sensor evidence |
| `GET /api/events?start=&end=` | The event feed for a window of at most 31 days, including decisions and outcomes |
| `GET /api/value` | The track record |
| `POST /api/field/supplier-message`, `GET /api/field/supplier-updates`, `GET /api/field/samples` | Supplier messages read into delivery updates; samples |
| `POST /api/alerts/{id}/inspection`, `GET /api/alerts/{id}/inspections` | Inspection photos read against the failure mode |
| `POST /api/alerts/{id}/feedback`, `GET /api/alerts/{id}/feedback?as_of=` | Mark an alert as false with a reason; its own and earlier verdicts, with the caution note |
| `GET /api/proposals`, `POST /api/proposals/{id}/status`, `POST /api/proposals/reset` | The approval queue |
| `GET /api/proposals/outcomes?as_of=` | Outcomes of approved decisions at the clock |
| `POST /api/agent/stream` | An agent run (`mode`: `single` or `team`) as server-sent events, then the checked answer |

## Deploying to Google Cloud

One container: a Node stage builds the React app, the Python stage generates all data at build time, and uvicorn serves the API, the agent stream, and the app on Cloud Run's port. `PROJECT_ID=<id> make deploy` enables the APIs and creates a service account allowed only to call Vertex AI, and runs one instance at most, because the demo keeps its state in the container. It then deploys from source, so no key is deployed. `docs/HANDOVER.md` has every step, check, cost, and the teardown.

**Usage limit.** The live app is public, so every call that reaches Gemini (agent runs, photo inspections, supplier messages) counts against two caps: 10 per visitor and 60 in total per hour by default (`USAGE_LIMIT_PER_VISITOR`, `USAGE_LIMIT_TOTAL`, `USAGE_LIMIT_WINDOW_MINUTES`; 0 turns a cap off). The total cap is the guarantee that nobody can drain the project's credit. A refused run says so in plain words and when to try again, and the autopilot stops itself.

## Ground rules

- **Synthetic data only.** Every dataset comes from a seeded generator in this repository. No real client or employer data, schemas, or names are used.
- **Reproducible.** `data/` is not committed; the same seeds recreate identical data on any machine. pandas stays below 3 and scikit-learn on 1.7 so the documented results hold.
- **Governed numbers.** Metrics are defined once in `semantic/`; models only choose among governed definitions.
