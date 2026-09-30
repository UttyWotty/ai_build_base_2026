"""Command line that replays the prediction test period as alerts and draft work orders, and prints the OEE lift.

Drafts go to the simulated CMMS outbox (data/outbox/work_order_drafts.json) for approval in the command center;
the full replay, including each alert's backtest truth, goes to data/alerts/replay.json.
"""
from __future__ import annotations

from dataclasses import asdict

from pdm_oee.core.work_order_rules import Outcome
from pdm_oee.data_pipeline.cmms_outbox import write_outbox
from pdm_oee.data_pipeline.replay_store import write_replay
from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.services.alert_service import AlertService
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.prediction_service import PredictionService
from pdm_oee.services.settings import OUTBOX_PATH, REPLAY_PATH, SEMANTIC_DIR

TRUTH_COLUMNS = ("truth", "failure_at")
PERCENT = 100


def main() -> int:
    catalog = load_catalog(SEMANTIC_DIR)
    prediction = PredictionService(catalog)
    backtest = prediction.backtest()
    replay = AlertService(catalog, prediction, OEEService(catalog, prediction.connection_manager)).replay(backtest)
    alerts, lift = replay.alerts, replay.lift
    print(f"{len(alerts)} alerts: {alerts['truth'].value_counts().to_dict()}")
    print(f"Outcomes: {alerts['outcome'].value_counts().to_dict()}; priorities: {alerts['priority'].value_counts().to_dict()}")
    print(f"Planned slots found for {int(alerts['planned_slot'].sum())} alerts\n")
    print(f"OEE {lift.oee_before * PERCENT:.2f}% -> {lift.oee_after * PERCENT:.2f}%, "
          f"availability {lift.availability_before * PERCENT:.2f}% -> {lift.availability_after * PERCENT:.2f}%")
    print(f"Recovered {lift.recovered_minutes / 60:.0f} h, inspections {lift.inspection_minutes / 60:.0f} h. Assumptions:")
    for assumption in lift.assumptions:
        print(f"  - {assumption}")
    drafts = alerts[alerts["outcome"] == Outcome.NEW_DRAFT.value].drop(columns=list(TRUTH_COLUMNS))
    write_outbox(drafts.to_dict("records"), OUTBOX_PATH)
    write_replay({"alerts": alerts.to_dict("records"), "lift": asdict(lift)}, REPLAY_PATH)
    print(f"\nOutbox: {OUTBOX_PATH} ({len(drafts)} drafts); replay: {REPLAY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
