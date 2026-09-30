"""The alert replay on the small plant: every alert is complete, consistent with the rules, and the lift is coherent.

Alert counts on 12 weeks are small; the checks are structural and hold for any number of alerts above zero.
The threshold is lowered for this test so the test block surely has alerts to check.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.work_order_rules import Outcome
from pdm_oee.services.alert_service import AlertService
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.prediction_service import PredictionService

LOW_THRESHOLD_QUANTILE = 0.99


def test_replay_alerts_follow_the_rules(prediction: PredictionService, catalog: PlantCatalog) -> None:
    backtest = prediction.backtest()
    eligible = backtest.panel["eligible"].to_numpy() & backtest.blocks["test"]
    low = float(np.quantile(backtest.scores["model"][eligible], LOW_THRESHOLD_QUANTILE))
    backtest = replace(backtest, validation={**backtest.validation, "model": replace(backtest.validation["model"], threshold=low)})
    replay = AlertService(catalog, prediction, OEEService(catalog, prediction.connection_manager)).replay(backtest)
    alerts = replay.alerts
    assert len(alerts) > 0
    assert (alerts["deadline_at"] > alerts["raised_at"]).all()
    assert set(alerts["outcome"]) <= {o.value for o in Outcome}
    planned = alerts[alerts["planned_slot"]]
    assert ((planned["slot_start"] >= planned["raised_at"]) & (planned["slot_end"] <= planned["deadline_at"])).all()
    for row in alerts.itertuples():
        mode = next(c.failure_modes[row.failure_mode] for c in catalog.plant.asset_classes.values() if row.failure_mode in c.failure_modes)
        assert [e["sensor"] for e in row.evidence] == list(mode.symptoms)
    lift = replay.lift
    assert 0 < lift.oee_before < 1 and 0 < lift.availability_before <= 1
    assert (lift.recovered_minutes > lift.inspection_minutes) == (lift.availability_after > lift.availability_before)
