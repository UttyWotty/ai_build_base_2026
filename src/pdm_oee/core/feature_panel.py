"""The hourly prediction panel: one row per asset, predictable failure mode, and hour, with features, label, and eligibility.

Features for a mode come from its symptom sensors in reaction order (s1 = first to react), as trailing rolling windows
over normalised hourly values, plus hours since the component's last repair. The decision is taken at the end of the hour.
A row is labelled positive when that mode fails within the horizon after the decision, and is eligible for training and
scoring only when the asset is not down, every symptom sensor has a completed baseline, and the label is not censored.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.prediction_settings import PredictionSettings

HOUR = pd.Timedelta(hours=1)
STATS = ("mean_short", "max_short", "mean_long", "trend")
MIN_SHORT_SHARE = 0.25


def symptom_count(catalog: PlantCatalog) -> int:
    return max(len(m.symptoms) for c in catalog.plant.asset_classes.values() for m in c.failure_modes.values())


def feature_names(catalog: PlantCatalog) -> list[str]:
    """Model inputs, in a fixed order: mode code, per-symptom statistics, hours since repair."""
    return ["mode_code", *[f"s{i + 1}_{stat}" for i in range(symptom_count(catalog)) for stat in STATS], "hours_since_repair"]


def mode_codes(catalog: PlantCatalog) -> dict[str, int]:
    modes = sorted(m.id for c in catalog.plant.asset_classes.values() for m in c.failure_modes.values() if m.predictable)
    return {mode: index for index, mode in enumerate(modes)}


def sensor_features(hourly: pd.DataFrame, settings: PredictionSettings) -> pd.DataFrame:
    """Trailing rolling statistics per sensor over the normalised hourly values."""
    hourly = hourly.sort_values(["sensor_id", "hour"]).reset_index(drop=True)
    grouped = hourly.groupby("sensor_id")["value"]
    short_min = max(1, int(settings.short_window_hours * MIN_SHORT_SHARE))
    hourly["mean_short"] = grouped.transform(lambda s: s.rolling(settings.short_window_hours, min_periods=short_min).mean())
    hourly["max_short"] = grouped.transform(lambda s: s.rolling(settings.short_window_hours, min_periods=short_min).max())
    hourly["mean_long"] = grouped.transform(lambda s: s.rolling(settings.long_window_hours, min_periods=settings.short_window_hours).mean())
    hourly["trend"] = hourly["mean_short"] - hourly["mean_long"]
    return hourly


def build_panel(features: pd.DataFrame, assets: pd.DataFrame, failures: pd.DataFrame, catalog: PlantCatalog,
                settings: PredictionSettings) -> pd.DataFrame:
    """Every asset x predictable mode x hour row, sorted by asset, mode, and hour."""
    codes, frames = mode_codes(catalog), []
    indexed = features.set_index(["asset_id", "sensor"])
    for asset in assets.itertuples():
        for mode in catalog.plant.asset_classes[asset.asset_class].failure_modes.values():
            if mode.predictable:
                frames.append(_mode_rows(asset.asset_id, mode, indexed, failures, codes[mode.id], settings))
    panel = pd.concat(frames, ignore_index=True)
    for i in range(symptom_count(catalog)):
        for stat in STATS:
            panel[f"s{i + 1}_{stat}"] = panel.get(f"s{i + 1}_{stat}", np.nan)
    return panel


def _mode_rows(asset_id: str, mode: object, features: pd.DataFrame, failures: pd.DataFrame, code: int,
               settings: PredictionSettings) -> pd.DataFrame:
    first = features.loc[(asset_id, mode.symptoms[0])]
    rows = pd.DataFrame({"asset_id": asset_id, "failure_mode": mode.id, "mode_code": code, "hour": first["hour"].to_numpy()})
    ages = []
    for position, sensor in enumerate(mode.symptoms, start=1):
        block = features.loc[(asset_id, sensor)]
        for stat in STATS:
            rows[f"s{position}_{stat}"] = block[stat].to_numpy()
        ages.append(block["epoch_age_hours"].to_numpy())
    decision = rows["hour"] + HOUR
    own = failures[(failures["asset_id"] == asset_id) & (failures["failure_mode"] == mode.id)].sort_values("failed_at")
    repairs = failures[(failures["asset_id"] == asset_id) & (failures["component"] == mode.component)]["restored_at"].sort_values()
    rows["hours_since_repair"] = _hours_since(decision, repairs, rows["hour"].iloc[0])
    rows["next_failure_at"] = _next_after(decision, own["failed_at"])
    rows["time_to_failure_hours"] = (rows["next_failure_at"] - decision) / HOUR
    rows["label"] = (rows["time_to_failure_hours"] > 0) & (rows["time_to_failure_hours"] <= settings.horizon_hours)
    down = _inside(rows["hour"], failures[failures["asset_id"] == asset_id])
    ready = np.min(np.vstack(ages), axis=0) >= settings.baseline_hours
    censored = decision > rows["hour"].iloc[-1] + HOUR - pd.Timedelta(hours=settings.horizon_hours)
    rows["eligible"] = ~down & ready & ~censored.to_numpy()
    return rows


def _hours_since(decision: pd.Series, repairs: pd.Series, first_hour: pd.Timestamp) -> np.ndarray:
    marks = np.concatenate([[first_hour.to_datetime64()], repairs.to_numpy()])
    index = np.searchsorted(np.sort(marks), decision.to_numpy(), side="right") - 1
    return (decision.to_numpy() - np.sort(marks)[index]) / np.timedelta64(1, "h")


def _next_after(decision: pd.Series, failed: pd.Series) -> pd.Series:
    times = failed.to_numpy()
    index = np.searchsorted(times, decision.to_numpy(), side="right")
    result = np.full(len(decision), np.datetime64("NaT"), dtype="datetime64[ns]")
    found = index < len(times)
    result[found] = times[index[found]]
    return pd.Series(result, index=decision.index)


def _inside(hours: pd.Series, failures: pd.DataFrame) -> np.ndarray:
    """True for hours that overlap a breakdown of the asset."""
    down = np.zeros(len(hours), dtype=bool)
    start, end = hours.to_numpy(), (hours + HOUR).to_numpy()
    for failure in failures.itertuples():
        down |= (start < np.datetime64(failure.restored_at)) & (end > np.datetime64(failure.failed_at))
    return down
