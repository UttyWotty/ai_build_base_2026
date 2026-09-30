# Supply Chain Ontology: Design Plan

This document defines the ontology, the canonical metric definitions, the synthetic source systems, and the build order for this project.
It is the reference that code and tests are checked against, so every metric definition here is precise enough to hand-compute.
Open decisions are listed at the end and must be settled before the matching milestone starts.

## 1. The thesis

The same question gets different answers across teams because each team computes the metric its own way:
different date fields, different grains, different denominators, different currency handling.
The fix this project demonstrates is structural, not a better prompt:

1. **One ontology.** Business entities and relationships are declared once, in YAML, with keys and join paths.
2. **One definition per metric.** Each canonical metric has exactly one formula, grain, time attribution rule, and filter set.
3. **The LLM never writes SQL.** It translates a question into a structured query spec (metric ids, dimensions, filters, time range) restricted to the catalog. A deterministic compiler turns that spec into SQL. The same metric id always compiles to the same SQL, so the same question from any persona produces the same number.

The last point is also what makes a local 27B model viable: choosing from a catalog and filling JSON is far more reliable than free-form text-to-SQL.

## 2. Ontology

### 2.1 Entities

| Entity | Key | Core attributes | Source system |
|---|---|---|---|
| Supplier | supplier_id | name, country, region, tier, currency | ERP, supplier portal |
| Part | part_id | description, category, family, uom, standard_cost_usd | ERP |
| SupplierPart | (supplier_id, part_id) | unit_price_local, moq, contracted_lead_time_days | ERP |
| Plant | plant_id | name, country, region | ERP |
| Customer | customer_id | name, segment, country, region | ERP |
| PurchaseOrderLine | po_line_id | po_id, supplier_id, part_id, plant_id, qty_ordered, order_date, promised_date | ERP, supplier portal |
| Receipt | receipt_id | po_line_id, inbound_shipment_id, qty_received, receipt_date | ERP |
| SalesOrder | so_id | customer_id, order_date, status | ERP |
| SalesOrderLine | so_line_id | so_id, part_id, plant_id, qty_ordered, order_date, requested_date, committed_date, status | ERP |
| Shipment | shipment_id | direction (inbound/outbound), carrier, origin, destination, ship_date, delivered_date, freight_cost_usd | TMS |
| OutboundShipmentLine | shipment_line_id | shipment_id, so_line_id, qty_shipped | TMS |
| InventorySnapshot | (plant_id, part_id, snapshot_date) | qty_on_hand | ERP (weekly) |
| FxRate | (currency, rate_date) | usd_per_unit | Treasury feed |
| DutyRate | (origin_country, category) | duty_pct | Trade compliance table |

### 2.2 Relationships (the chain in the brief)

```
Supplier --supplies--> SupplierPart <--is sourced as-- Part
Supplier --receives--> PurchaseOrderLine --for--> Part, --delivered to--> Plant
PurchaseOrderLine --fulfilled by--> Receipt --arrived on--> Shipment (inbound)
Plant --stocks--> InventorySnapshot --of--> Part
Customer --places--> SalesOrder --contains--> SalesOrderLine --for--> Part, --fulfilled from--> Plant
SalesOrderLine --shipped on--> OutboundShipmentLine --part of--> Shipment (outbound)
```

Every relationship declares its cardinality and join keys, and joins on the parent's full key. The compiler only joins along declared relationships.

**Unique join paths.** Validation fails if any entity can reach another by two different declared paths, because the compiler could otherwise pick different routes on different days. Three modelling choices follow from this rule:

- A sales order line reaches its customer only through its sales order header; it does not carry its own `customer_id`.
- Inbound goods are modelled as `Receipt -> Shipment`, and only outbound movements have shipment lines. A single shipment-line entity pointing at both PO lines and SO lines would reach `Part` two ways.
- Purchase order lines carry their own price and do not join to `SupplierPart`, because that would give a second route to `Supplier`.

**Derived attributes.** Flags and rollups such as `is_delivered_complete_by_committed` or `landed_cost_usd` are marked `derived: true`. The conform pipeline computes them, and their description in `ontology.yaml` is the governing definition that the pipeline tests are written against.

### 2.3 Hierarchies

- **Geography:** region -> country -> plant (and region -> country -> supplier / customer)
- **Product:** category -> family -> part
- **Time:** year -> quarter -> month -> ISO week -> date

### 2.4 Business model scope (v1)

The model is a distribution-style manufacturer with no bill of materials. Plants buy parts, stock them, and sell the same parts to customers.
Adding a BOM is a v2 extension. It changes the days-of-inventory basis from shipped cost to consumption cost, but leaves the rest of the ontology unchanged.

## 3. Canonical metrics

Each metric has a single definition. Near-miss variants that teams commonly confuse with it are declared as **separate named metrics**, never as silent aliases.
That separation is how the project demonstrates governance.

### 3.1 On-time delivery (OTD), customer

- **Grain:** sales order line.
- **Population:** lines with status not `cancelled` whose `committed_date` falls in the period.
- **On time:** cumulative delivered qty reaches `qty_ordered` on or before `committed_date` (delivered = the shipment's `delivered_date`, not its `ship_date`).
- **Formula:** on-time lines / population lines, count-weighted.
- **Time attribution:** `committed_date`.
- **Not the same as:** `supplier_otd` (below), `carrier_on_time` (shipment delivered vs planned transit), or OTD measured against `requested_date` (declared as `otd_vs_request`).

### 3.2 Supplier on-time delivery (supplier_otd)

- **Grain:** purchase order line.
- **Population:** PO lines whose `promised_date` falls in the period.
- **On time:** cumulative received qty reaches `qty_ordered` on or before `promised_date`.
- **Formula:** on-time lines / population lines.
- **Time attribution:** `promised_date`.

### 3.3 Fill rate

- **Canonical:** unit fill rate.
- **Grain:** sales order line.
- **Population:** non-cancelled lines whose first outbound shipment `ship_date` falls in the period.
- **Formula:** sum(qty on the line's first shipment) / sum(qty_ordered).
- **Time attribution:** first `ship_date`.
- **Declared variants:** `line_fill_rate` (lines complete on first shipment / lines) and `order_fill_rate` (orders whose lines are all complete on first shipment / orders).

### 3.4 Days of inventory (DOI)

- **Grain:** plant x part, rolled up by summing numerator and denominator (never by averaging ratios).
- **Numerator:** on-hand value at period end = `qty_on_hand` x `standard_cost_usd`, using the last snapshot on or before period end.
- **Denominator:** average daily COGS over the trailing 90 days ending at period end, where COGS = outbound shipped qty x `standard_cost_usd`.
- **Formula:** numerator / denominator. If the denominator is zero, the result is null and reported as "no demand", never as infinity or zero.
- **Constant:** the trailing window of 90 days is a named, documented metric parameter.

### 3.5 Landed cost per unit

- **Grain:** receipt.
- **Components, all in USD:**
  - goods: `unit_price_local` x FX rate on `receipt_date` x `qty_received`
  - freight: the inbound shipment's `freight_cost_usd` allocated to its lines by goods value share
  - duty: goods value x `duty_pct` for (supplier country, part category)
- **Formula:** sum(goods + freight + duty) / sum(qty_received).
- **Time attribution:** `receipt_date`.
- **Not the same as:** `purchase_price_per_unit` (goods only).

### 3.6 Metric spec shape (YAML)

```yaml
id: otd
label: On-time delivery (customer)
description: "Share of non-cancelled customer order lines whose full quantity was delivered on or before the committed date."
owner: planning
type: ratio
grain: sales_order_line
time_dimension: committed_date
numerator: {aggregation: count_if, attribute: is_delivered_complete_by_committed}
denominator: {aggregation: count}
filters:
  - {attribute: status, operator: not_equals, value: cancelled}
format: percent
synonyms: [on time delivery, OTD, customer OTD, customer on time delivery, delivery performance]
not_to_be_confused_with: [otd_vs_request, supplier_otd, carrier_on_time]
```

Metrics are structured, not free-form expressions, so the validator can check every part of them.

- **Aggregations:** `sum` needs a numeric attribute, `count_if` a boolean one, and `count` counts grain rows.
- **Time and filters:** the time dimension must be a date attribute of the grain, and filter values must match the attribute's type.
- **Business terms:** every term (id, label, or synonym, compared after normalizing case and punctuation) must resolve to exactly one metric.

The spec shape is modelled on Snowflake semantic views (entities, dimensions, facts, metrics, synonyms). If the project ever moves back to Snowflake, the ontology can be exported to that format.

## 4. Synthetic source systems

Scattered, inconsistent data is the problem this project solves, so the generator deliberately produces inconsistent sources. A conform step then builds the ontology entities from them.

### 4.1 How the world is generated

The generator does not invent source rows independently. It first simulates one consistent business and only then renders that business as messy source exports:

1. **Master data:** plants, suppliers, parts, customers, supplier contracts, and which plants stock which parts.
2. **Demand:** sales order lines per plant-part and week, with requested and committed dates, grouped into orders.
3. **Weekly simulation per plant-part:** receive arrivals, ship backlog first-in-first-out from stock, take a snapshot, and reorder under a min-max policy.
   - Supplier confirmations, revisions, and delivery delays come from per-supplier reliability.
   - Shortages therefore produce real backorders, partial shipments, and late lines, so fill rate and OTD emerge from the simulation rather than being drawn at random.
4. **Logistics:** carriers, transit, delays, and freight for inbound and outbound shipments.
5. **Assembly:** canonical truth tables, one per ontology entity with exactly its non-derived attributes, written to `data/truth/`.
6. **Rendering:** the truth is rendered into source exports under `data/sources/`.

The truth tables exist for testing only. The conform pipeline (milestone 3) must never read them; its tests compare its output against them.

### 4.2 Source systems and their traps

| System | Files | Deliberate inconsistencies |
|---|---|---|
| ERP | `erp/*.xlsx` (masters), `erp/*.parquet` (transactions) | Composite ids split into document and item number; single-letter status codes; no promised dates; receipts know shipments only by bill of lading |
| TMS | `tms/shipments.parquet`, `tms/outbound_lines.parquet` | Partner codes instead of ERP numbers; `IB`/`OB` direction codes; part numbers without the `P-` prefix; packaging quantities in cases; event times as UTC strings, whose calendar date can differ from the local date; freight billed in the plant currency |
| Supplier portal | `supplier_portal/confirmations.xlsx` | One row per confirmation or revision (latest by confirmation time wins); supplier names spelled differently from the ERP; `DD/MM/YYYY` text dates |
| Treasury | `treasury/fx_rates.xlsx` | Rates quoted as currency units per USD (the ontology stores USD per unit) |
| Trade | `trade/duty_rates.xlsx` | Duty in percent (the ontology stores a fraction) |
| MDM | `mdm/partner_crosswalk.xlsx` | The only bridge from TMS partner codes to ERP numbers |

Every trap has a round-trip test in `tests/synthetic/test_renderers.py` showing how to resolve it back to the truth. Those tests are the specification for the conform step.

### 4.3 Scale (default seed)

| Measure | Value |
|---|---|
| Master data | 40 suppliers, 300 parts, 4 plants, 120 customers |
| History | 104 weeks from 2024-09-30 |
| Transactions | about 60k sales order lines in 30k orders, 10k PO lines, 10k receipts, 55k shipments, 43k weekly inventory rows |
| Performance | generates in about 10 seconds; 8 MB on disk |

### 4.4 Planted stories

| Story | What the default seed shows |
|---|---|
| Supplier degradation | The largest supplier (`V10001`) falls from about 91% supplier OTD to about 66% after a one-quarter ramp starting in 2026 Q1; peers stay near 89% |
| Freight spike | Inbound freight on the CN to US01 lane runs about 1.8x normal in 2025 Q4, lifting landed cost for parts sourced that way |
| Overstock | DE01 holds Bearings at about 124 days of inventory against about 25 days elsewhere |
| Request gap | Aftermarket customers request lead times shorter than transit, so `otd_vs_request` (about 60%) sits well below `otd` (about 78%) |

### 4.5 Determinism

One seed drives every random draw in a fixed order.
- **Same seed, same data:** Parquet files are byte-identical across runs.
- **xlsx files:** contain zip timestamps, so they are compared by content fingerprint instead. `data/manifest.json` records the fingerprint and row count of every file, the seed, the full config, and the story facts.

## 5. Architecture

```
src/supply_ontology/
  core/            pure: ontology + metric models, YAML validation, spec -> SQL compiler
  data_pipeline/   generator (sources), conform (sources -> entities), DuckDB adapter
  services/        query service (spec -> result), NL service (question -> spec via llm_client)
  api/endpoints/   FastAPI routes
semantic/          ontology.yaml, metrics/*.yaml, personas.yaml  (the governed layer, versioned)
```

### Conform rules (milestone 3)

- Every transformation is a pure function over frames. `source_reader` and `conformed_store` are the only file I/O.
- Unmapped keys, unknown codes, unknown units, and FX gaps raise `ConformError`. Nothing is silently dropped or nulled.
- xlsx sources are read with only empty cells treated as missing, because pandas' defaults turn the region code `NA` into NaN.
- Derived attributes follow their `ontology.yaml` descriptions exactly. Each rule has a hand-computed test in `tests/conform/test_derived_attributes.py`.
- The output must reproduce every truth table. It is checked per entity both in memory and through a real file round trip.

### Compiler rules

- Aggregate at the metric's grain first, then join to coarser dimensions. This prevents fan-out double counting.
- Ratios roll up as sum(numerator) / sum(denominator), never as an average of ratios.
- Only declared relationships can be joined. A requested dimension with no path to the metric's grain is a validation error, not a guess.
- **As-of rule:** rows whose time attribution falls after the data's as-of date are excluded, because their outcome is not known yet. The as-of date is the latest inventory snapshot. Without this rule, lines committed for next month would count as late today.
- Period-end metrics keep only the last time value in each period (or in the time range when there is no grain), selected before any dimension joins.
- Every value is a bound parameter. Identifiers are validated snake_case, so the SQL never needs quoting and never contains user text.

### NL layer

1. Governed wording binds the metric before the model runs. The longest governed phrase in the question wins, including the persona's jargon, and the model cannot override it.
2. The prompt contains the metric catalog (ids, labels, synonyms, not-to-be-confused-with lists), the governed dimensions with their values, and named calendar anchors computed from the as-of date. The system message is the same for every question and persona.
3. The local model returns a JSON decision: a query spec, a clarifying question, or a refusal. Grain, time range, and dimensions are kept only when the question's wording supports them. The spec must pass compiler validation and the governance checks (governed dimensions only, filter values that exist). On invalid output the model gets one retry with the problems.
4. If a phrase could mean several metrics (for example "on time" could mean `otd`, `supplier_otd`, or `carrier_on_time`), context words in the question settle it only when they point to exactly one candidate. Otherwise the service asks a clarifying question instead of guessing.
5. The response shows the resolved metric id, its definition, the SQL fingerprint, and whether the wording or the model chose the metric.

### Personas

`personas.yaml` gives planning, procurement, and logistics their own synonyms and default dimensions. Every persona maps to the same metric ids, and personas cannot redefine a metric.

## 6. The consistency demo

1. **The problem, reproduced:** the same question ("what was our on-time delivery last quarter?") is sent through naive text-to-SQL on the raw source tables, once per persona prompt. The answers differ because each run picks a different date column, grain, or source.
2. **The fix:** the same three phrasings go through the governed layer. All three resolve to `otd`, compile to identical SQL (hash shown), and return the same number.
3. **The boundary:** "on-time for suppliers" resolves to `supplier_otd`, a different declared metric with its own definition, which shows that governance is not just aliasing.

Next to the live naive run, three illustrative team recipes (`demo/team_recipes.yaml`) reproduce the disagreement deterministically, so the demo does not depend on how the model behaves on the day.
Each recipe states which choices differ from the governed definition. Two of them land on declared variants (`otd_vs_request` and `carrier_on_time`), which is the thesis in one table: every team's shortcut is a real metric, just not the one being asked about.

The naive half is given a fair chance: the prompt shows every raw table with sample values and today's date, and asks for a single `answer` column expressed as a fraction.
Model-written SQL runs on a DuckDB connection with external access disabled and the configuration locked, under a time limit and a row cap.
Only one `SELECT` or `WITH` statement is accepted from a reply.
A naive query that fails or returns no value gets one retry with the problem, the same single retry the governed path gets. Date columns are shown with their full range, because sample values alone led the model to guess the wrong year.

## 7. Testing

| Layer | Tests |
|---|---|
| core | YAML validation, relationship paths, query spec parsing and validation |
| compiler | Golden values for all ten metrics on a hand-built world (`tests/compiler/golden_world.py`): join paths, grains, filters, period end, zero denominators, the as-of rule, determinism, bound parameters |
| data_pipeline | Generator determinism (same seed, same hash), crosswalk completeness, planted stories present |
| services | Spec validation and clarification logic with a stub `llm_client` |
| conform | Every entity equals its truth table; hand-computed derived attribute cases; loud failures for unmapped data |
| synthetic | Weekly stock balance, quantity and date invariants, round trip of every source trap, planted stories, determinism |
| integration | Truth tables match the ontology's non-derived attributes, keys are unique, every relationship resolves, writer is byte-deterministic |
| Evaluation (not unit tests) | A golden question set per persona -> expected spec; accuracy of the local model tracked over time |

## 8. Milestones

1. **Ontology and metric YAML + validator** (core, pure, tested)
2. **Synthetic source generator** with inconsistencies and planted stories
3. **Conform pipeline** -> entity Parquet + DuckDB views, crosswalk tests
4. **Compiler** spec -> SQL, golden tests for all five canonical metrics and declared variants
5. **NL service** on the local model: spec generation, validation retry, clarification
6. **Consistency demo** including the naive text-to-SQL contrast
7. **UI** for question, resolved definition, SQL, and result

## 9. Decisions (settled 2026-09-29)

1. **No BOM in v1** (section 2.4).
2. **Canonical OTD is measured against the committed date.** Requested-date OTD is the declared variant `otd_vs_request`.
3. **The semantic layer is our own YAML plus compiler.** The format is modelled on Snowflake semantic views so it can be exported later.
4. **The UI is Streamlit.**
