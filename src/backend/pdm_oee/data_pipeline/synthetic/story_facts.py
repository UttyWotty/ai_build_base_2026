"""Measures each planted story in the generated truth tables, so the manifest states what the data actually shows.

Facts are computed from the tables, not copied from the configuration: a story that failed to appear shows up here.
Tests assert on these facts, and the demo questions of later milestones refer to them.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.masters import sensor_id

SMALL_STOP_LIMIT = pd.Timedelta(minutes=5)
SUMMER_MONTHS = (6, 7, 8)
WINTER_MONTHS = (12, 1, 2)
CNC_CLASS = "cnc_machining_centre"
CONVEYOR_CLASS = "conveyor_drive"


@dataclass(frozen=True)
class StoryFacts:
    """What each story looks like in the generated data."""

    bearing_failed_at: str
    pump_failed_at: str
    calibration_sensor_id: str
    calibration_at: str
    over_maintained_pm_per_asset: float
    other_pm_per_asset: float
    over_maintained_failures_per_asset: float
    other_failures_per_asset: float
    coolant_line_summer_scrap_share: float
    coolant_line_winter_scrap_share: float
    small_stop_asset_stops_per_shift: float
    other_conveyor_stops_per_shift: float


def story_facts(tables: dict[str, pd.DataFrame], stories: StoryConfig) -> StoryFacts:
    """Measure every story in the truth tables."""
    assets, failures, orders = tables["asset"], tables["failure_event"], tables["work_order"]
    line_assets = set(assets.loc[assets["line_id"] == stories.over_maintained_line_id, "asset_id"])
    preventive = orders[orders["work_type"] == "preventive"]
    instrument = orders[orders["work_type"] == "instrument"].iloc[0]
    return StoryFacts(
        bearing_failed_at=_failed_at(failures, stories.bearing_asset_id, "spindle_bearing_wear"),
        pump_failed_at=_failed_at(failures, stories.pump_asset_id, "hydraulic_pump_wear"),
        calibration_sensor_id=sensor_id(stories.calibration_asset_id, stories.calibration_sensor),
        calibration_at=str(instrument["created_at"]),
        over_maintained_pm_per_asset=_per_asset(preventive, line_assets),
        other_pm_per_asset=_per_asset(preventive, set(assets["asset_id"]) - line_assets),
        over_maintained_failures_per_asset=_per_asset(failures, line_assets),
        other_failures_per_asset=_per_asset(failures, set(assets["asset_id"]) - line_assets),
        **_coolant_facts(tables, stories),
        **_small_stop_facts(tables, stories),
    )


def _failed_at(failures: pd.DataFrame, asset_id: str, mode: str) -> str:
    match = failures[(failures["asset_id"] == asset_id) & (failures["failure_mode"] == mode)]
    return str(match["failed_at"].max())


def _per_asset(frame: pd.DataFrame, asset_ids: set[str]) -> float:
    return round(float(frame["asset_id"].isin(asset_ids).sum()) / max(1, len(asset_ids)), 2)


def _coolant_facts(tables: dict[str, pd.DataFrame], stories: StoryConfig) -> dict[str, float]:
    assets = tables["asset"]
    cncs = assets[(assets["line_id"] == stories.coolant_line_id) & (assets["asset_class"] == CNC_CLASS)]["asset_id"]
    counts = tables["production_count"].merge(tables["shift"][["shift_id", "shift_date"]], on="shift_id")
    counts = counts[counts["asset_id"].isin(cncs)]
    months = pd.to_datetime(counts["shift_date"]).dt.month

    def share(selected: pd.Series) -> float:
        chosen = counts[selected]
        return round(float(chosen["scrap_count"].sum()) / max(1, int(chosen["total_count"].sum())), 4)

    return {"coolant_line_summer_scrap_share": share(months.isin(SUMMER_MONTHS)),
            "coolant_line_winter_scrap_share": share(months.isin(WINTER_MONTHS))}


def _small_stop_facts(tables: dict[str, pd.DataFrame], stories: StoryConfig) -> dict[str, float]:
    states, assets = tables["machine_state"], tables["asset"]
    short = states[(states["state"] == "unplanned_stop") & (states["end_at"] - states["start_at"] < SMALL_STOP_LIMIT)]
    shifts_per_asset = tables["production_count"].groupby("asset_id").size()
    conveyors = assets.loc[assets["asset_class"] == CONVEYOR_CLASS, "asset_id"]
    rates = short.groupby("asset_id").size().reindex(conveyors, fill_value=0) / shifts_per_asset.reindex(conveyors)
    story = stories.small_stop_asset_id
    return {"small_stop_asset_stops_per_shift": round(float(rates.get(story, 0.0)), 2),
            "other_conveyor_stops_per_shift": round(float(rates.drop(story, errors="ignore").median()), 2)}
