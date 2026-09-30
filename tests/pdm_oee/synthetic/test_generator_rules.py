"""Focused tests of the generator's pure rules: symptom timing, the coolant season, local time, and failure overlap.

These pin the rules the stories depend on, independently of any particular seed.
Each test builds its inputs by hand.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.synthetic.local_time import to_local
from pdm_oee.data_pipeline.synthetic.reliability import (
    Degradation,
    _one_repair_at_a_time,
)
from pdm_oee.data_pipeline.synthetic.seasonal import coolant_rise
from pdm_oee.data_pipeline.synthetic.sensors import symptom_start


def test_symptoms_start_in_reaction_order(catalog: PlantCatalog) -> None:
    mode = catalog.plant.asset_classes["cnc_machining_centre"].failure_modes["spindle_bearing_wear"]
    onset, failed = 0, 6 * 1440
    assert symptom_start(mode, "spindle_vibration", onset, failed) == onset
    assert symptom_start(mode, "spindle_temperature", onset, failed) == 4 * 1440


def test_coolant_rise_peaks_in_summer_and_never_cools() -> None:
    days = np.arange(1, 366)
    story, normal = coolant_rise(days, True, 6.0), coolant_rise(days, False, 6.0)
    assert (story >= 0).all() and story.max() == story[199] and abs(story.max() - 6.0) < 1e-9
    assert story[10] == 0 and normal.max() < story.max()


def test_local_time_follows_daylight_saving() -> None:
    utc = pd.Series(pd.to_datetime(["2026-01-15 12:00", "2026-07-15 12:00"]))
    assert list(to_local(utc, pd.Series(["US1", "US1"])).dt.hour) == [6, 7]
    assert list(to_local(utc, pd.Series(["DE1", "DE1"])).dt.hour) == [13, 14]


def test_a_failure_during_an_open_repair_is_dropped() -> None:
    first = Degradation("A", "c", "m1", None, 100, 200, False)
    during = Degradation("A", "c", "m2", None, 150, 260, False)
    touching = Degradation("A", "c", "m2", None, 200, 300, False)
    other_asset = Degradation("B", "c", "m1", None, 150, 250, False)
    kept = _one_repair_at_a_time([first, during, other_asset, touching])
    assert kept == [first, other_asset]
