"""Data rules of the prediction panel on the small plant: no look-ahead, labels, eligibility, and re-baselining.

Deleting every reading after a moment must not change any feature before it; labels mark failures within the horizon;
rows during breakdowns or inside a baseline window are ineligible; a sensor swap starts a new baseline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.feature_panel import sensor_features
from pdm_oee.core.sensor_hours import epoch_starts, hourly_values, running_readings
from pdm_oee.services.prediction_service import PredictionService
from tests.pdm_oee.prediction.conftest import SMALL_SETTINGS

SENSOR = "US1-L2-01/spindle_vibration"


def features_for(conformed: dict, catalog: PlantCatalog, cut: pd.Timestamp | None, instrument: pd.DataFrame | None = None) -> pd.DataFrame:
    readings = conformed["sensor_reading"]
    if cut is not None:
        readings = readings[readings["ts"] < cut]
    sensors = conformed["sensor"]
    hours = pd.date_range(conformed["sensor_reading"]["ts"].min().floor("h"), conformed["sensor_reading"]["ts"].max().floor("h"), freq="h")
    orders = conformed["work_order"]
    instrument = orders[orders["work_type"] == "instrument"] if instrument is None else instrument
    running = running_readings(readings, sensors, conformed["machine_state"])
    epochs = epoch_starts(sensors, conformed["failure_event"], instrument, hours[0])
    return sensor_features(hourly_values(running, sensors, conformed["asset"], epochs, hours, catalog, SMALL_SETTINGS), SMALL_SETTINGS)


def test_features_never_look_ahead(conformed: dict, catalog: PlantCatalog) -> None:
    cut = pd.Timestamp("2025-11-20 13:00")
    full = features_for(conformed, catalog, None)
    trimmed = features_for(conformed, catalog, cut)
    before = full["hour"] < cut
    columns = ["value", "mean_short", "max_short", "mean_long", "trend"]
    assert np.allclose(full.loc[before, columns].to_numpy(dtype=float), trimmed.loc[before, columns].to_numpy(dtype=float), equal_nan=True)


def test_labels_and_eligibility(prediction: PredictionService, conformed: dict) -> None:
    panel = prediction.panel
    positives = panel[panel["label"]]
    assert ((positives["time_to_failure_hours"] > 0) & (positives["time_to_failure_hours"] <= SMALL_SETTINGS.horizon_hours)).all()
    failure = conformed["failure_event"].iloc[0]
    during = panel[(panel["asset_id"] == failure["asset_id"]) & (panel["hour"] >= failure["failed_at"].floor("h"))
                   & (panel["hour"] < failure["restored_at"])]
    assert len(during) and not during["eligible"].any()
    first_days = panel["hour"] < panel["hour"].min() + pd.Timedelta(hours=SMALL_SETTINGS.baseline_hours)
    assert not panel.loc[first_days, "eligible"].any()


def test_sensor_swap_starts_a_new_baseline(conformed: dict, catalog: PlantCatalog, small_world) -> None:
    sensor = small_world.story_facts.calibration_sensor_id
    swapped = pd.Timestamp(small_world.story_facts.calibration_at)
    after = slice(swapped + pd.Timedelta(hours=SMALL_SETTINGS.baseline_hours), swapped + pd.Timedelta(days=28))
    swapped_run = features_for(conformed, catalog, None)
    with_swap = swapped_run[swapped_run["sensor_id"] == sensor].set_index("hour")["value"][after]
    plain_run = features_for(conformed, catalog, None, conformed["work_order"].iloc[0:0])
    without = plain_run[plain_run["sensor_id"] == sensor].set_index("hour")["value"][after]
    assert abs(with_swap.mean()) < 0.1 and without.mean() - with_swap.mean() > 0.15
