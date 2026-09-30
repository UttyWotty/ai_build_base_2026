"""Replays the predictor's test-period alerts as draft work orders and estimates what acting on them would have been worth.

Each alert start becomes one record with evidence in engineering units, a deadline, a planned slot or an unplanned stop,
a priority, and a dedup outcome; its truth (useful, late, false) comes from the backtest. Caught failures feed the lift.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pdm_oee.core.alert_scoring import alert_starts, scoring_context
from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import MachineState
from pdm_oee.core.lift_replay import LiftEstimate, estimate, recovered_minutes
from pdm_oee.core.sensor_hours import running_readings
from pdm_oee.core.work_order_rules import (
    Outcome,
    deadline,
    dedup,
    open_alert,
    planned_slot,
    priority,
)
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.prediction_service import Backtest, PredictionService

INSPECTION_HOURS = 1.0
MINUTES_PER_HOUR = 60
EVIDENCE_WINDOW = pd.Timedelta(hours=24)
HOUR = pd.Timedelta(hours=1)
USEFUL, LATE, FALSE = "useful", "late", "false"
EVIDENCE_DECIMALS = 2


@dataclass(frozen=True)
class AlertReplay:
    alerts: pd.DataFrame
    lift: LiftEstimate


class AlertService:
    """Alerts, drafts, and the lift estimate for the prediction test period."""

    def __init__(self, catalog: PlantCatalog, prediction: PredictionService, oee: OEEService) -> None:
        self.catalog, self.prediction, self.oee = catalog, prediction, oee
        tables = prediction.tables
        self.running = running_readings(tables["sensor_reading"], tables["sensor"], tables["machine_state"])
        states = tables["machine_state"]
        self.planned_stops = states[states["state"] == MachineState.PLANNED_STOP.value]

    def replay(self, backtest: Backtest) -> AlertReplay:
        settings, panel = self.prediction.settings, backtest.panel
        threshold = backtest.validation["model"].threshold
        starts = alert_starts(scoring_context(panel), backtest.scores["model"], threshold, settings.quiet_hours) & backtest.blocks["test"]
        rows = panel[starts].assign(score=backtest.scores["model"][starts]).sort_values(["hour", "asset_id"])
        records: list[dict] = []
        for row in rows.itertuples():
            records.append(self._alert(row, records))
        alerts = pd.DataFrame(records)
        return AlertReplay(alerts, self._lift(alerts, backtest))

    def _alert(self, row: object, earlier: list[dict]) -> dict:
        tables, settings = self.prediction.tables, self.prediction.settings
        asset = tables["asset"].set_index("asset_id").loc[row.asset_id]
        mode = self.catalog.plant.asset_classes[asset["asset_class"]].failure_modes[row.failure_mode]
        raised = row.hour + HOUR
        due = deadline(raised, mode.pf_interval_days, settings.horizon_hours)
        slot = planned_slot(self.planned_stops[self.planned_stops["asset_id"] == row.asset_id], raised, due, mode.repair_hours)
        attached = open_alert(earlier, row.asset_id, mode.id, raised)
        outcome, attached = (Outcome.ATTACHED_TO_OPEN_ALERT, attached) if attached else dedup(
            tables["work_order"], row.asset_id, mode.component, raised, due)
        lead = row.time_to_failure_hours
        truth = USEFUL if settings.min_lead_hours <= lead <= settings.horizon_hours else LATE if 0 < lead < settings.min_lead_hours else FALSE
        return {"alert_id": f"AL-{row.asset_id}-{raised:%Y%m%d%H}", "asset_id": row.asset_id, "failure_mode": mode.id,
                "component": mode.component, "raised_at": raised, "score": round(float(row.score), 4), "deadline_at": due,
                "criticality": asset["criticality"], "priority": priority(asset["criticality"], slot).value,
                "slot_start": slot.start, "slot_end": slot.end, "planned_slot": slot.planned, "repair_hours": mode.repair_hours,
                "recommended_action": mode.recommended_action, "outcome": outcome.value, "attached_wo_id": attached,
                "evidence": self._evidence(row.asset_id, mode.symptoms, asset["asset_class"], raised),
                "truth": truth, "failure_at": row.next_failure_at if truth != FALSE else pd.NaT}

    def _evidence(self, asset_id: str, symptoms: tuple[str, ...], asset_class: str, raised: pd.Timestamp) -> list[dict]:
        window = self.running[(self.running["asset_id"] == asset_id) & (self.running["ts"] >= raised - EVIDENCE_WINDOW)
                              & (self.running["ts"] < raised)]
        spec_class = self.catalog.plant.asset_classes[asset_class]
        evidence = []
        for sensor in symptoms:
            spec = spec_class.sensors[sensor]
            values = window.loc[window["sensor"] == sensor, "value"]
            evidence.append({"sensor": sensor, "label": spec.label, "unit": self.catalog.plant.sensor_types[spec.sensor_type].unit.value,
                             "mean_24h": None if values.empty else round(float(values.mean()), EVIDENCE_DECIMALS),
                             "normal_low": spec.normal_range[0], "normal_high": spec.normal_range[1]})
        return evidence

    def _lift(self, alerts: pd.DataFrame, backtest: Backtest) -> LiftEstimate:
        failures = self.prediction.tables["failure_event"]
        useful = alerts[alerts["truth"] == USEFUL].sort_values("raised_at").drop_duplicates(["asset_id", "failure_mode", "failure_at"])
        caught = useful.merge(failures, left_on=["asset_id", "failure_mode", "failure_at"], right_on=["asset_id", "failure_mode", "failed_at"])
        in_shift = pd.Series({f.failure_id: self._in_shift_minutes(f) for f in caught.itertuples()}, dtype=float)
        caught = caught.assign(recovered=recovered_minutes(caught, in_shift).to_numpy())
        false_unplanned = alerts[(alerts["truth"] == FALSE) & ~alerts["planned_slot"] & (alerts["outcome"] == Outcome.NEW_DRAFT.value)]
        inspections = false_unplanned.groupby("asset_id").size() * INSPECTION_HOURS * MINUTES_PER_HOUR
        test_start = backtest.panel.loc[backtest.blocks["test"], "hour"].min().date()
        measures = self.oee.measures[self.oee.period(test_start, None)]
        return estimate(measures, caught.groupby("asset_id")["recovered"].sum(), inspections, INSPECTION_HOURS)

    def _in_shift_minutes(self, failure: object) -> float:
        site = self.prediction.tables["asset"].set_index("asset_id").loc[failure.asset_id, "site_id"]
        shifts = self.oee.tables["shift"]
        mine = shifts[(shifts["site_id"] == site) & (shifts["end_at"] > failure.failed_at) & (shifts["start_at"] < failure.restored_at)]
        overlap = mine["end_at"].clip(upper=failure.restored_at) - mine["start_at"].clip(lower=failure.failed_at)
        return float((overlap / pd.Timedelta(minutes=1)).sum())
