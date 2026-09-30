"""Preventive maintenance windows and instrument work: when each asset is serviced and when the story sensor is swapped.

Preventive service is routine (lubrication, filters, inspection) and does not reset component wear, so it cannot prevent
random-onset failures; the over-maintained line simply loses more planned time. Some services slip past their due date.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.synthetic.calendar import MINUTES_PER_DAY
from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.errors import GenerationError
from pdm_oee.data_pipeline.synthetic.reference import (
    PM_HOURS,
    PM_INTERVAL_DAYS,
    PM_LATE_DAYS,
    PM_LATE_SHARE,
)

MINUTES_PER_HOUR = 60
FIRST_DUE_SHARE = (0.2, 1.0)


@dataclass(frozen=True)
class InstrumentWork:
    """A sensor replaced on a given minute; readings after it carry the calibration offset."""

    asset_id: str
    sensor: str
    minute: int
    offset: float


def plan_preventive(assets: pd.DataFrame, shifts: pd.DataFrame, stories: StoryConfig, horizon: int,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Every preventive service: due day, and the window it was actually done in (the first shift on or after it)."""
    rows = []
    for asset in assets.itertuples():
        factor = stories.over_maintenance_interval_factor if asset.line_id == stories.over_maintained_line_id else 1.0
        interval = PM_INTERVAL_DAYS[asset.asset_class] * factor
        due_day = interval * rng.uniform(*FIRST_DUE_SHARE)
        starts = shifts.loc[shifts["site_id"] == asset.site_id, "start_minute"].to_numpy()
        while due_day * MINUTES_PER_DAY < horizon:
            late_days = int(rng.integers(PM_LATE_DAYS[0], PM_LATE_DAYS[1] + 1)) if rng.random() < PM_LATE_SHARE else 0
            done_after = int((int(due_day) + late_days) * MINUTES_PER_DAY)
            later = starts[starts >= done_after]
            duration = int(PM_HOURS[asset.asset_class] * MINUTES_PER_HOUR)
            if len(later) and later[0] + duration <= horizon:
                rows.append({"asset_id": asset.asset_id, "due_day": int(due_day), "start_minute": int(later[0]),
                             "end_minute": int(later[0]) + duration})
            due_day += interval
    return pd.DataFrame(rows)


def plan_instrument_work(assets: pd.DataFrame, stories: StoryConfig, horizon: int) -> list[InstrumentWork]:
    """The calibration story: one sensor replaced with an offset, and no failure behind it."""
    if stories.calibration_asset_id not in set(assets["asset_id"]):
        raise GenerationError(f"Calibration story asset {stories.calibration_asset_id} does not exist")
    minute = stories.calibration_day * MINUTES_PER_DAY
    if minute >= horizon:
        raise GenerationError(f"Calibration story day {stories.calibration_day} is outside the horizon")
    return [InstrumentWork(stories.calibration_asset_id, stories.calibration_sensor, minute, stories.calibration_offset)]
