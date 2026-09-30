"""Golden reliability values: MTBF, MTTR, and PM compliance on hand-built failures and work orders.

A1 ran 10 hours in the period and had two failures (3 h and 1 h to restore): MTBF 5 h, MTTR 2 h.
Of two preventive tasks due in the period, one closed on its due date and one a day late: compliance 50%.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.metric_rollup import rollup
from pdm_oee.core.reliability_measures import component_measures, preventive_measures

START, END = pd.Timestamp("2026-01-05"), pd.Timestamp("2026-01-06")


def test_mtbf_and_mttr(catalog: PlantCatalog) -> None:
    states = pd.DataFrame({"asset_id": "A1", "state": ["running", "unplanned_stop", "running"],
                           "start_at": pd.to_datetime(["2026-01-04 20:00", "2026-01-05 06:00", "2026-01-05 09:00"]),
                           "end_at": pd.to_datetime(["2026-01-05 06:00", "2026-01-05 09:00", "2026-01-05 13:00"])})
    failures = pd.DataFrame({"asset_id": "A1", "component": "spindle_bearing",
                             "failed_at": pd.to_datetime(["2026-01-05 06:00", "2026-01-05 13:00"]),
                             "restored_at": pd.to_datetime(["2026-01-05 09:00", "2026-01-05 14:00"])})
    components = pd.DataFrame({"asset_id": ["A1", "A1"], "component": ["spindle_bearing", "coolant_pump"]})
    measures = component_measures(states, failures, components, START, END)
    bearing = rollup(measures[measures["component"] == "spindle_bearing"], catalog, ["mtbf", "mttr"], [])
    assert bearing["mtbf"].iloc[0] == pytest.approx(10 / 2) and bearing["mttr"].iloc[0] == pytest.approx(2)
    assert rollup(measures[measures["component"] == "coolant_pump"], catalog, ["mtbf"], []).isna().all().all()


def test_pm_compliance(catalog: PlantCatalog) -> None:
    orders = pd.DataFrame({"asset_id": "A1", "work_type": "preventive",
                           "due_date": [date(2026, 1, 5), date(2026, 1, 5), date(2026, 2, 1)],
                           "closed_at": pd.to_datetime(["2026-01-05 12:00", "2026-01-06 12:00", "2026-02-01 12:00"])})
    measures = preventive_measures(orders, pd.DataFrame({"asset_id": ["A1"]}), date(2026, 1, 1), date(2026, 1, 31))
    assert rollup(measures, catalog, ["pm_compliance"], [])["pm_compliance"].iloc[0] == pytest.approx(0.5)
