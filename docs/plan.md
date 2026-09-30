# Plan

This document states the problem the operations copilot solves, how it is built, and the milestones that deliver it.
It is the source of truth for scope: each milestone ends in a release that works on its own.
The entry targets the AI Builder Cup 2026, Manufacturing track, with a submission deadline of 2026-10-18.

## 1. Problem

When a machine is about to fail, the maintenance, supply, and sales teams each see one piece of the problem in their own system:
- **Maintenance** sees a vibration trend, if anyone is watching it.
- **Stores and purchasing** see a spare part's stock level and a supplier's promised date, not that a failure is coming.
- **Customer service** sees the promised delivery dates, not that the line making the goods is about to stop.

So the question that matters ("this spindle will fail in about a day; do we have the bearing, and whose orders slip if we don't?") takes hours of calls to answer. Meanwhile the P-F interval, the warning time between a detectable fault and the failure, runs out. Most AI demos answer one of these questions. This project connects them.

## 2. Solution

An operations copilot on Google Cloud that runs a closed sense, reason, act loop over governed operational data:

1. **Sense.** A failure-prediction model scores every asset from its sensor history and raises an alert with a lead time.
2. **Reason.** A team of Gemini agents (Google Agent Development Kit) investigates the alert with governed tools only:
   - a maintenance planner: the asset's sensor evidence, inspection photos read by Gemini vision, and its history
   - a procurement lead: the spare's stock at both sites, the alerts queued for it, every way to get it, and the
     supplier's governed on-time delivery, revised by supplier messages Gemini has read
   - a customer service lead: the customer order lines the affected line serves in the downtime window
   - an operations lead: weighs the three briefs and decides
3. **Act.** The lead proposes a work order, a parts action (stock, open order, transfer, express buy, or new order),
   and a customer note. A person approves or rejects. An approval becomes a decision that moves stock and clears
   conflicts from its moment on, and its outcome is settled against the real failure once the clock passes it.

No model writes SQL or invents a number. Every figure comes from a governed metric or a deterministic tool, and each
answer shows the tools it used and whether its numbers were verified.

## 3. Starting point

The repository joins two finished component packages, imported at their latest releases:

| Package | Imported from | What it brings |
|---|---|---|
| `pdm_oee` | pdm-oee-command-center v0.8.3 | A two-site plant simulation, the OEE engine, failure prediction (27 of 41 failures caught at 0.16 false alerts per asset-month), draft work orders, natural-language investigation |
| `supply_ontology` | supply-chain-ontology v0.7.2 | A four-plant supply network simulation, the governed ontology and metrics, a deterministic SQL compiler, governed natural-language questions |

The two simulations already line up:
- Both horizons end on 2026-09-28.
- Plant sites US1 and DE1 correspond to supply plants US01 and DE01.
- The supply network stocks the bearing, hydraulic, and electrical parts that the plant's failure modes consume.

The bridge (`semantic/bridge/bridge.yaml`) gives each site a small maintenance spares store. The plant's own repairs
consume it, and it is replenished from supply-network suppliers, arriving as late as those suppliers really deliver there.
This produces the demo moment without any extra planting:
- Supplier V10001, which supplies the spindle bearing sets, has been on time for only 66% of its lines in the 90 days before 2026-07-25.
- At 02:00 that day, US1 has two open spindle-bearing alerts, on US1-L3-01 (raised 07-20) and US1-L2-01 (the planted six-day failure, raised that hour).
- US1 has one bearing set on the shelf; the replacement ordered from V10001 on 07-19 is promised for 08-02. DE1 has one set.

The copilot's answer: the overdue US1-L3-01 alert takes the set, and an air transfer from DE1 covers US1-L2-01 for 650 USD. Waiting for V10001's order would mean 190 hours of downtime, 94 thousand USD of lost contribution, and four customer order lines at risk.

## 4. Architecture

```
semantic/{pdm,supply,bridge}     governed definitions: plant model, ontology, metrics, cross-domain links
src/backend/pdm_oee              plant: simulation, conform, OEE, prediction, alerts
src/backend/supply_ontology      supply: simulation, conform, metric compiler, governed questions
src/backend/llm_gateway          model gateway: Gemini or local model
src/backend/copilot              bridge, impact, track record, decisions, field inputs, agents, HTTP API
  core/                          pure logic: impact rules, decisions and outcomes, value, events, instructions
  data_pipeline/                 adapters: world store, bridge files, record stores, samples
  services/                      impact, value, decisions, field inputs, event feed, agents and team
  api/ ui/                       FastAPI endpoints and CLIs; the earlier Streamlit app
src/frontend                     React web app
```

Layers import downward only: `api`/`ui` -> `services` -> `data_pipeline` -> `core`. The copilot imports the component packages' services, never the reverse.

Google Cloud mapping (see `docs/HANDOVER.md` for the steps):

| Concern | Local development | Google Cloud |
|---|---|---|
| Reasoning model | Gemini through an AI Studio key, or a local OpenAI-compatible model | Gemini on Vertex AI, authenticated by the Cloud Run service account |
| Agent | Google Agent Development Kit | Same code |
| App hosting | `make api` and `make web` | Cloud Run, one container serving the API and the React app |
| Analytical data | DuckDB over Parquet | DuckDB inside the container first; BigQuery as the warehouse mode |
| Files | `data/` | Cloud Storage |
| Sensor events (stretch) | Replay from Parquet | Pub/Sub topic feeding the alert service |

## 5. Milestones

| Version | Milestone | Done when |
|---|---|---|
| 0.1.0 | Monorepo foundation | Both packages imported with namespaced data, settings, and tests; one `make test` and `make lint`; both worlds regenerate identically to the source repos |
| 0.2.0 | Model layer | One model setting selects Gemini (AI Studio key or Vertex) or a local model for every language feature |
| 0.3.0 | Bridge and impact | `semantic/bridge/` links sites, components, spare parts, and products; a point-in-time impact service answers parts availability, supplier risk, transfer options, and orders at risk |
| 0.4.0 | Operations agent | An ADK agent with governed tools turns an alert into an action plan for approval; an evaluation set scores its tool use and its numbers |
| 0.5.0 | Web app | One app: alerts, the agent's trace, approvals, and a demo clock |
| 0.6.0 | Cloud-ready | Container, Cloud Run deployment script, Vertex configuration, and `docs/HANDOVER.md` |
| 0.7.0 | Submission kit | Write-up covering the judging criteria, demo script, architecture diagram (0.2.0 to 0.7.0 released together as 0.7.0) |
| 0.8.0 | Finals-grade product | React and FastAPI in one container; the track record; live mode with an autopilot; the closed loop from approval to outcome; multimodal Gemini (supplier inbox, inspection photos); the four-agent team; backup models and plain-language errors |

Before the 2026-10-18 submission (the team): the first Cloud Run deploy, sample inspection photos, the full Gemini
evaluation, and the demo video. These are P0 in `techdebt.md`.

After the submission, for the Top 200 architecture sprints and the Top 50 round: Firestore for approvals and field
inputs, BigQuery for the conformed data, Pub/Sub for the live event stream, Vertex AI for the failure model, and Cloud
Monitoring for the agents. These are P1 in `techdebt.md`.

## 6. Judging criteria and where they are met

| Criterion | Where it is met |
|---|---|
| The problem and why it matters | Section 1; the demo opens with a 2 a.m. alert that nobody is awake to see |
| How the solution addresses it | The closed loop shown end to end on one week of the plant, then the track record over four months (net 197,949 USD) |
| Google AI and agentic integration | A four-agent team on ADK (parallel specialists, sequential lead), multimodal Gemini for photos and supplier messages, streamed traces, verified numbers |
| A functional prototype | Seven-page React app over FastAPI on synthetic data, with 430 automated tests and an agent evaluation set |
| Deployment on Google Cloud | One Cloud Run service with Gemini on Vertex AI, reproducible from `docs/HANDOVER.md` |
