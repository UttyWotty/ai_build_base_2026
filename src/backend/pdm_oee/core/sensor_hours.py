"""Hourly sensor values for prediction: running readings only, normalised to each sensor's own post-repair baseline.

A sensor's baseline epoch restarts at the horizon start, after every repair on its asset, and after its own replacement,
so a sensor swap with a calibration offset looks like a new normal, not like wear. The baseline is the median of the
epoch's first baseline_hours of running values; until that window is complete the normalised value is undefined, so no
hour ever depends on later data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import MachineState
from pdm_oee.core.prediction_settings import PredictionSettings

HOUR = pd.Timedelta(hours=1)
GOOD = "good"


def running_readings(readings: pd.DataFrame, sensors: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    """Good readings taken while their asset was running."""
    good = readings[readings["quality"] == GOOD].merge(sensors[["sensor_id", "asset_id", "sensor"]], on="sensor_id")
    marks = states[["asset_id", "start_at", "state"]].sort_values("start_at")
    joined = pd.merge_asof(good.sort_values("ts"), marks, left_on="ts", right_on="start_at", by="asset_id", direction="backward")
    return joined[joined["state"] == MachineState.RUNNING.value][["sensor_id", "asset_id", "sensor", "ts", "value"]]


def epoch_starts(sensors: pd.DataFrame, failures: pd.DataFrame, instrument_orders: pd.DataFrame, first_hour: pd.Timestamp) -> dict[str, np.ndarray]:
    """Sorted epoch start hours per sensor."""
    result = {}
    for sensor in sensors.itertuples():
        restores = failures.loc[failures["asset_id"] == sensor.asset_id, "restored_at"]
        swaps = instrument_orders.loc[(instrument_orders["asset_id"] == sensor.asset_id) & (instrument_orders["sensor"] == sensor.sensor), "created_at"]
        hours = pd.concat([pd.Series([first_hour]), restores.dt.ceil("h"), swaps.dt.ceil("h")])
        result[sensor.sensor_id] = np.sort(hours.unique())
    return result


def hourly_values(running: pd.DataFrame, sensors: pd.DataFrame, assets: pd.DataFrame, epochs: dict[str, np.ndarray],
                  hours: pd.DatetimeIndex, catalog: PlantCatalog, settings: PredictionSettings) -> pd.DataFrame:
    """One row per sensor and hour: normalised value (NaN when not running or inside a baseline window) and epoch age."""
    means = running.assign(hour=running["ts"].dt.floor("h")).groupby(["sensor_id", "hour"])["value"].mean()
    classes = assets.set_index("asset_id")["asset_class"]
    frames = []
    for sensor in sensors.itertuples():
        spec = catalog.plant.asset_classes[classes[sensor.asset_id]].sensors[sensor.sensor]
        values = means.get(sensor.sensor_id, pd.Series(dtype=float)).reindex(hours).to_numpy(dtype=float)
        starts = epochs[sensor.sensor_id]
        index = np.searchsorted(starts, hours.to_numpy(), side="right") - 1
        age = (hours.to_numpy() - starts[index]) / np.timedelta64(1, "h")
        normalised = np.full(len(hours), np.nan)
        width = spec.normal_range[1] - spec.normal_range[0]
        for epoch in np.unique(index):
            inside = index == epoch
            window = inside & (age < settings.baseline_hours)
            baseline = np.nanmedian(values[window]) if np.isfinite(values[window]).any() else np.nan
            ready = inside & (age >= settings.baseline_hours)
            normalised[ready] = (values[ready] - baseline) / width
        frames.append(pd.DataFrame({"sensor_id": sensor.sensor_id, "asset_id": sensor.asset_id, "sensor": sensor.sensor,
                                    "hour": hours, "value": normalised, "epoch_age_hours": age}))
    return pd.concat(frames, ignore_index=True)
