# Predictive Maintenance and OEE Command Center: Design Plan

This document defines the plant model, the OEE and reliability definitions, the failure prediction setup, the synthetic source systems, and the build order.
It is the reference that code and tests are checked against, so every metric here is precise enough to hand-compute.
Decisions are listed at the end; each has a stated default that holds until it is changed.

## 1. The thesis

Equipment usually warns before it fails: a bearing's vibration rises days before it seizes.
The warning sits in the OT historian, while the context that makes it actionable sits elsewhere: the production schedule and ideal cycle times in the ERP, stops and counts in the MES, repairs in the CMMS.
Kept apart, the result is the familiar pattern: breakdowns that surprise everyone, preventive maintenance done by calendar rather than condition, and OEE losses nobody can attribute.

The project shows four things, each measured rather than asserted:

1. **One plant model.** Assets, components, sensors, failure modes, and loss reasons are declared once, in YAML, and every source is conformed to it.
2. **One definition per metric.** Availability, performance, quality, OEE, MTBF, and MTTR each have exactly one formula, and look-alikes are declared separately, as in the sibling supply chain project.
3. **Failures predicted with usable lead time.** The model is judged on failures caught at least 24 hours ahead within a fixed alert budget, not on row-level accuracy.
4. **Predictions turned into action.** Each alert becomes a draft work order, scheduled into the next planned stop. The OEE lift is estimated by replaying the year with and without the alerts.

The local language model explains and investigates. It never computes a metric or writes SQL: it chooses from a closed catalog of governed tools, as in the sibling project.

## 2. Plant model

### 2.1 Physical hierarchy

```
Site --has--> Line --has--> Asset --has--> Component --measured by--> Sensor
AssetClass --defines--> Component types, Sensor types, Failure modes
```

| Level | Default scale | Notes |
|---|---|---|
| Site | 2 | `US1` (Central time, sensors in imperial units) and `DE1` (Berlin time, metric units) |
| Line | 3 per site | Each line runs one product family |
| Asset | 4 per line, 24 in total | Classes below |
| Component | 2 to 3 per asset | The unit that fails and is repaired |
| Sensor | 2 to 4 per asset | Historian tags |

### 2.2 Asset classes

| Class | Components | Sensors | Failure modes |
|---|---|---|---|
| `cnc_machining_centre` | spindle bearing, coolant pump, tool changer | spindle vibration (mm/s RMS), spindle temperature, spindle speed, coolant temperature | bearing wear, pump cavitation, tool changer jam |
| `hydraulic_press` | hydraulic pump, main seal | hydraulic pressure, pressure ripple, oil temperature | pump wear, seal leak |
| `conveyor_drive` | gearbox, drive motor | motor current, gearbox vibration, motor temperature | gearbox wear, motor overheating |

Each failure mode declares its component, its symptom sensors (in the order they react), a typical P-F interval (the time from first detectable symptom to functional failure), a repair time, and the recommended corrective action.
Failure modes without a sensor signature (the tool changer jam) are declared as such. They count in MTBF but are excluded from prediction, so the predictor is never scored on failures it could not see.

### 2.3 Entities

| Entity | Key | Core attributes | Source system |
|---|---|---|---|
| Site, Line, Asset, Component, Sensor | ids | names, class, criticality (A/B/C), install dates, units | Asset register |
| SensorReading | (sensor_id, ts) | value in canonical units, quality flag | Historian |
| MachineState | (asset_id, start_ts) | state (running, idle, down, planned_stop, setup), reason code, end_ts | MES |
| ProductionCount | (asset_id, shift_id) | total_count, scrap_count | MES |
| Shift | shift_id | site, start_ts, end_ts, planned break minutes | MES calendar |
| ProductionOrder | order_id | line, product, quantity, planned start and end | ERP |
| Product | product_id | family, ideal cycle time per asset class | ERP routing |
| WorkOrder | wo_id | asset, component, type (corrective, preventive, predictive), failure mode code, created, started, closed, labour hours, free text | CMMS |
| FailureEvent | failure_id | asset, component, failure mode, failed_at, restored_at | Derived from MES down states and corrective work orders |

## 3. Metrics

All time metrics are computed per asset and shift, then rolled up by summing numerators and denominators. Ratios are never averaged across assets or shifts.

### 3.1 Time model

```
calendar time
  minus planned stops (breaks, planned maintenance, no production scheduled)  = planned production time
  minus availability losses (breakdowns, setup and changeover, stops >= 5 min) = run time
```

- **Small stops:** stops shorter than 5 minutes are a performance loss, not an availability loss. The threshold is a named metric parameter.
- **Idle:** time idle because the asset is starved or blocked counts as an availability loss, attributed to the upstream or downstream cause.

### 3.2 Canonical metrics

| Metric id | Formula | Grain | Time attribution |
|---|---|---|---|
| `availability` | run time / planned production time | asset x shift | shift start |
| `performance` | (ideal cycle time x total count) / run time | asset x shift | shift start |
| `quality` | good count / total count, where good = total - scrap and rework counts as scrap | asset x shift | shift start |
| `oee` | ideal cycle time x good count / planned production time, which equals A x P x Q per asset and shift | asset x shift | shift start |
| `mtbf` | operating hours / number of functional failures | asset x component | failure time |
| `mttr` | total repair hours / number of repairs | asset x component | restore time |
| `pm_compliance` | preventive work orders completed by due date / due | asset | due date |

**Rolling OEE above one asset.** OEE is rolled up as sum(ideal cycle time x good count) / sum(planned production time), not as the product of rolled-up A, P, and Q.

**Declared look-alikes.** These are separate named metrics, never aliases:
- `teep`: OEE over calendar time instead of planned production time.
- `availability_incl_small_stops`: availability with the 5-minute threshold removed.
- `oee_nameplate`: OEE using the nameplate speed instead of the product's ideal cycle time.

**Validation.** A performance value above 1.0 means the ideal cycle time is wrong. The validator reports it and never caps it.

### 3.3 Loss taxonomy

Every lost minute or part is booked to exactly one loss, and every loss to exactly one OEE factor. The losses are the six big losses plus external stops, which keeps starved, blocked, and no-operator stops out of breakdowns:

| Loss | Factor | Source |
|---|---|---|
| Breakdowns | availability | stop reasons |
| Setup and adjustments | availability | stop reasons |
| External stops | availability | stop reasons |
| Small stops | performance | any loss stop shorter than 5 minutes |
| Reduced speed | performance | the gap between ideal and actual cycle time |
| Startup rejects | quality | scrap after a startup or changeover |
| Production rejects | quality | other scrap |

- **Planned stop reasons** (break, planned maintenance, no production scheduled) are not losses; they leave planned production time.
- **What fails validation:** a stop reason booked to a derived loss, and an availability loss with no reason. MES reason codes that don't map to a governed reason fail conform. The loss waterfall must reconcile exactly: planned production time minus the losses equals the valuable operating time behind OEE.

## 4. Failure prediction

### 4.1 Framing

- **Decision point:** the end of every operating hour, for every asset and predictable failure mode.
- **Label:** positive if that failure mode's functional failure occurs within the next 7 days (the horizon, a named parameter).
- **Excluded rows:** hours while the asset is down or under repair, the first 14 days after a repair of that component (the baseline window), and the last 7 days of data, whose labels are censored.
- **No look-ahead:** features use only readings timestamped at or before the decision point, as the historian delivered them, including gaps and bad-quality flags.

### 4.2 Features

- Rolling 24-hour and 7-day mean, maximum, and slope of each symptom sensor.
- Each sensor normalised to its own asset's post-repair baseline, so assets are comparable.
- Operating hours since the component's last repair, and the load regime (speed or pressure band).
- Only good-quality readings taken while the asset was running count, so an idle weekend or a broken sensor looks like missing data, not like health.
- **Re-baselining:** a sensor's baseline restarts after every repair on its asset and after its own replacement, so the calibration story's offset becomes the new normal instead of a false alarm. Values inside an unfinished baseline window are undefined, which is what keeps every feature free of look-ahead.

### 4.3 Models and evaluation

- **Two models:**
  - an interpretable baseline: a per-failure-mode health index (the worst normalised symptom) against a threshold
  - a scikit-learn `HistGradientBoostingClassifier`
- **Time-based split:** fit the classifier on the first six months, choose each predictor's threshold on the next two, and test once on the last four. Never a random split, and the threshold is never chosen on the model's own training rows.
- **Event-level scoring:** a failure counts as caught when an alert for its asset and failure mode fires between 7 days and 24 hours before it. Alerts are raised when the score crosses a threshold and are suppressed while one is open for the same asset and failure mode.
- **Alert budget:** the threshold is chosen on training data to allow at most one false alert per asset per month.
- **Reported:** caught failures / evaluable failures (those at least one eligible row could have warned in time), false alerts per asset-month, late alerts, median lead time, and the same for the baseline. The model has to beat the baseline to be used.
- **Long P-F intervals:** a failure mode whose P-F interval is longer than the horizon (the hydraulic pump's 21 days) can raise correct warnings more than seven days out, and these are scored as false. The scoring stays conservative rather than moving the horizon per mode.

## 5. From alert to action

1. **Draft work order.** An alert produces one draft work order with:
   - the asset, component, and failure mode
   - the evidence: each symptom sensor's running mean over the last day, in engineering units, next to its healthy range
   - the failure mode's recommended action
2. **Deadline.** The repair is due half the failure mode's P-F interval after the alert (the usual P-F/2 rule), capped at the 7-day horizon.
3. **Scheduling.** The suggested slot is the first planned stop (weekend, holiday, or preventive window) that starts after the alert, fits the repair, and ends by the deadline. If there is none, the draft asks for an unplanned stop of the repair's length.
4. **Priority.** P1 for criticality-A assets with no slot, P2 for criticality A or no slot, P3 otherwise.
5. **Deduplication.** An alert is attached, not drafted, when it arrives while:
   - an earlier draft for the same asset and mode is still before its deadline
   - a corrective order on the component is open
   - a preventive task on the asset is due by the deadline
6. **Nothing leaves the repo.** Drafts are written to a simulated CMMS outbox and approved or dismissed in the UI.
7. **OEE lift, estimated by replay** over the test period, with its assumptions stated next to the number:
   - a caught failure repaired in a planned slot costs no production time
   - one without a slot costs its planned repair time instead of its real breakdown
   - a false alert that needs an unplanned stop costs a one-hour inspection
   - recovered minutes produce at the asset's own performance and quality

## 6. Synthetic source systems

### 6.1 How the plant is generated

As in the sibling project, one consistent plant is simulated first and only then rendered as messy source exports:

1. **Master data:** sites, lines, assets, components, sensors, products, and ideal cycle times.
2. **Production schedule and shifts:** ERP orders per line and a shift calendar with planned stops.
3. **Degradation:** each component carries a hidden wear state. After a random onset it rises along the failure mode's curve until failure, and a repair resets it. A failure that would start while the asset is still being repaired is folded into that repair.
   - **Preventive maintenance** is routine service (lubrication, filters, inspection) and does not reset wear. Calendar-based service cannot prevent random-onset failures, which is the reliability-centred maintenance case for condition monitoring. It is also why the over-maintained line loses planned time without gaining reliability.
4. **Sensors:** each symptom sensor reads baseline + load-regime effect + wear effect + noise, sampled as 10-minute historian aggregates over one year.
5. **Operations:** machine states from failures, planned stops, changeovers, small stops, and starvation; counts and scrap from run time, cycle time, and quality drivers.
6. **Maintenance:** corrective work orders for failures and preventive orders by interval, with realistic delays and free text.
7. **Truth and rendering:** canonical truth tables are written to `data/truth/` for tests only, and source exports to `data/sources/`.

### 6.2 Source systems and their traps

| System | Files | Deliberate inconsistencies |
|---|---|---|
| Asset register | `asset_register/*.xlsx` | Human-readable asset names; the only bridge to historian tag paths |
| Historian | `historian/readings.parquet` | Tag paths such as `US1.L2.CNC01.SPDL_VIB` instead of ids; US1 temperatures in degrees Fahrenheit and pressures in psi; site-specific quality codes; UTC timestamps; gaps, multi-hour outages, and bad-quality spikes; a sensor replaced mid-year with a calibration offset |
| MES | `mes/states.parquet`, `mes/counts.parquet`, `mes/reason_codes.xlsx`, `mes/shift_calendar.xlsx` | Local time with daylight-saving transitions, ordered only by a sequence number; state and reason codes that differ between sites; cumulative counters that reset at a shift start |
| ERP | `erp/products.xlsx`, `erp/routings_<site>.xlsx`, `erp/production_orders.xlsx` | Ideal speed in parts per hour at US1 and seconds per part at DE1; lines named "US1 Line 2" |
| CMMS | `cmms/work_orders.xlsx` | Asset numbers instead of ids; local times; failure codes missing on some corrective orders (free text only); closure dates entered days late; duplicate orders for one breakdown; the replaced sensor named only in free text |

Every trap gets a round-trip test showing how the conform step resolves it.

### 6.3 Planted stories

| Story | What it shows |
|---|---|
| Spindle bearing wear on a CNC asset at US1 | Vibration rises about 6 days before failure and temperature follows about 2 days later: a catchable failure |
| Hydraulic pump wear on a DE1 press | A slower P-F interval of about 3 weeks, visible in pressure ripple before oil temperature |
| Calibration offset after a sensor swap | A step change in one temperature sensor with no failure behind it; conform must use the CMMS record to separate it, or the model learns a false alarm |
| Over-maintenance on one line | Preventive maintenance at half the interval of its peers: twice the planned maintenance time (planned downtime, so it lowers planned production time and TEEP rather than availability), and no fewer failures |
| Coolant temperature and scrap | Scrap on one line rises with coolant temperature, a root-cause story for the language layer |
| Hidden small stops | A conveyor with frequent stops under 5 minutes: a performance loss invisible in the breakdown log |

### 6.4 Determinism

One seed drives every random draw in a fixed order. Parquet outputs are byte-identical across runs, and xlsx files are compared by content fingerprint in `data/manifest.json`.

## 7. Architecture

```
src/pdm_oee/
  core/            pure: plant model, metric and loss catalog, validators, OEE math, labels, alert and work-order rules
  data_pipeline/   generator (sources), conform (sources -> canonical tables), DuckDB adapter, LLM client, model store
  services/        OEE service, prediction and backtest service, alert and work-order service, investigation service
  api/             CLIs; the Streamlit command center sits above services
semantic/          plant.yaml, metrics/*.yaml, losses.yaml, failure_modes.yaml (the governed layer, versioned)
```

The layout matches `supply-chain-ontology`, so the two can later merge into one manufacturing analytics lab.

## 8. Natural-language investigation

- **Governed tools:** the local model gets a closed catalog of nine tools, each a deterministic query:
  - `oee_summary` and `oee_trend`
  - `loss_breakdown` and `top_loss_contributors`
  - `sensor_trend`
  - `failures` and `work_order_history`
  - `alerts`, from the saved replay
  - `quality_drivers`: weekly quality next to temperature sensors, with correlations
- **Validated calls:** arguments are checked against the known ids, sensors, losses, and dates before a tool runs. An invalid call, or a call the data cannot answer, goes back to the model with what to fix.
- **Each turn:** the model replies with one JSON tool call or a final answer, with at most six calls.
- **Number check:** every number in the final answer must match a tool result (as a value, or a ratio shown as a percentage, at the answer's precision). Dates, ids, and numbers from the question are ignored. An answer with an unexplained number gets one retry and is then marked unverified.
- **Evaluation:** ten questions in `evaluation/investigation.yaml`, each with the tools at least one of which must be used and the terms the answer must mention, such as "why did quality drop on line DE1-L2 in summer?" leading to `quality_drivers` and "coolant".

## 9. Testing

| Layer | Tests |
|---|---|
| core | YAML validation, OEE math on hand-built shifts, loss reconciliation, label and exclusion rules, dedup and scheduling rules |
| synthetic | Determinism, wear and sensor invariants, every source trap's round trip, planted stories present |
| conform | Every canonical table equals its truth table; loud failures for unmapped tags and codes |
| prediction | No look-ahead (features unchanged when future rows are deleted), event-level scoring on a hand-built timeline, the time split |
| services | Backtest and OEE lift on a small plant; the investigation loop with a scripted model |
| UI | The real page run headless with injected services |

## 10. Milestones

1. **Plant model and metric catalog:** asset classes, sensors, failure modes, losses, measures, and metrics in YAML with a validating catalog. Each metric is a ratio of two declared measures, so shared quantities such as run time have one definition.
2. **Synthetic plant generator:** degradation physics, source systems, planted stories
3. **Conform pipeline:** sources to canonical tables and DuckDB views
4. **OEE engine:** shift-level A, P, Q, OEE, and the loss waterfall, with golden tests
5. **Failure prediction:** labels, features, baseline and model, event-level backtest
6. **Alerts and work orders:** drafts, dedup, scheduling, simulated CMMS outbox, OEE lift by replay
7. **Natural-language investigation:** on the local model, with an evaluation set
8. **Command center UI:** Streamlit

## 11. Decisions (defaults set 2026-09-29)

Each default below holds until changed. They are listed so they can be overruled before the milestone they affect.

1. **Equipment:** CNC machining centres, hydraulic presses, and conveyor drives across two sites, deliberately unlike the injection moulding domain of any other project. (Milestone 1)
2. **Sensor grain:** 10-minute historian aggregates over one year, about 4 million readings. Raw high-frequency vibration is out of scope. (Milestone 2)
3. **Prediction:** a 7-day horizon, at least 24 hours of useful lead, and a budget of one false alert per asset per month. (Milestone 5)
4. **Learning library:** scikit-learn, with the interpretable baseline always reported alongside. (Milestone 5)
5. **Work orders:** only drafted into a simulated outbox and approved by a person; never written anywhere else. (Milestone 6)
6. **UI:** Streamlit, matching the sibling project. (Milestone 8)
