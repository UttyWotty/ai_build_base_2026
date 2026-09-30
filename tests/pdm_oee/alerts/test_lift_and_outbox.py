"""The OEE lift arithmetic by hand, and the simulated CMMS outbox's status rules.

Asset A: planned 1000 min, run 800, valuable 600 (0.75 per run minute). Recovering 100 minutes and spending 20 on
inspections adds 80 run minutes and 60 valuable minutes: OEE 0.60 -> 0.66, availability 0.80 -> 0.88.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pdm_oee.core.lift_replay import estimate, recovered_minutes
from pdm_oee.data_pipeline.cmms_outbox import (
    APPROVED,
    OutboxError,
    read_outbox,
    set_status,
    write_outbox,
)


def test_recovered_minutes_depend_on_the_slot() -> None:
    caught = pd.DataFrame({"failure_id": ["F1", "F2", "F3"], "planned_slot": [True, False, False], "repair_hours": [2.0, 2.0, 5.0]})
    minutes = recovered_minutes(caught, pd.Series({"F1": 300.0, "F2": 300.0, "F3": 120.0}))
    assert list(minutes) == [300.0, 180.0, 0.0]


def test_lift_estimate_by_hand() -> None:
    measures = pd.DataFrame({"asset_id": ["A", "A"], "planned_production_time": [500.0, 500.0], "run_time": [400.0, 400.0],
                             "valuable_operating_time": [300.0, 300.0]})
    lift = estimate(measures, pd.Series({"A": 100.0}), pd.Series({"A": 20.0}), inspection_hours=1.0)
    assert (lift.oee_before, lift.availability_before) == (0.6, 0.8)
    assert lift.oee_after == pytest.approx(0.66) and lift.availability_after == pytest.approx(0.88)
    assert any("1.0 h" in a for a in lift.assumptions)


def test_outbox_approves_known_drafts_only(tmp_path: Path) -> None:
    path = tmp_path / "outbox.json"
    write_outbox([{"alert_id": "AL-1", "asset_id": "A"}], path)
    assert read_outbox(path)[0]["status"] == "draft"
    assert set_status(path, "AL-1", APPROVED)["status"] == APPROVED and read_outbox(path)[0]["status"] == APPROVED
    with pytest.raises(OutboxError, match="No draft"):
        set_status(path, "AL-2", APPROVED)
    with pytest.raises(OutboxError, match="Unknown status"):
        set_status(path, "AL-1", "shipped")
