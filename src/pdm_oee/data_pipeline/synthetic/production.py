"""Part counts per asset and shift: what the running minutes produced, and how much of it was scrap.

Parts come only from running minutes, at the product's ideal cycle slowed by a per-shift speed factor.
Startup scrap follows a changeover; production scrap has a base rate, raised by hot coolant on the coolant story line.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.minute_states import RUNNING_CODE
from pdm_oee.data_pipeline.synthetic.reference import (
    BASE_SCRAP_SHARE,
    COOLANT_SCRAP_THRESHOLD,
    SPEED_FACTOR,
    STARTUP_MINUTES,
    STARTUP_SCRAP_SHARE,
)
from pdm_oee.data_pipeline.synthetic.seasonal import coolant_rise

SECONDS_PER_MINUTE = 60
COOLANT_BASE_C = 22.0
COOLANT_CLASS = "cnc_machining_centre"


def shift_counts(assets: pd.DataFrame, shifts: pd.DataFrame, line_shifts: pd.DataFrame, routings: pd.DataFrame,
                 minute_states: dict[str, np.ndarray], stories: StoryConfig, rng: np.random.Generator) -> pd.DataFrame:
    """Total, scrap, and startup scrap per asset and shift, for shifts in which the asset produced anything."""
    plan = line_shifts.merge(shifts[["shift_id", "start_minute", "end_minute", "shift_date"]], on="shift_id")
    cycle = routings.set_index(["product_id", "asset_class"])["ideal_cycle_s"]
    rows = []
    for asset in assets.itertuples():
        states = minute_states[asset.asset_id]
        story_line = asset.line_id == stories.coolant_line_id
        for shift in plan[plan["line_id"] == asset.line_id].itertuples():
            running = int((states[shift.start_minute:shift.end_minute] == RUNNING_CODE).sum())
            if running == 0:
                continue
            actual = cycle[(shift.product_id, asset.asset_class)] * rng.uniform(*SPEED_FACTOR)
            total = int(running * SECONDS_PER_MINUTE / actual)
            startup = min(total, int(STARTUP_MINUTES * SECONDS_PER_MINUTE / actual)) if shift.changeover else 0
            share = _scrap_share(asset.asset_class, story_line, shift.shift_date, stories)
            rows.append({"asset_id": asset.asset_id, "shift_id": shift.shift_id, "product_id": shift.product_id,
                         "order_id": shift.order_id, "total_count": total,
                         "startup_scrap_count": int(rng.binomial(startup, STARTUP_SCRAP_SHARE)),
                         "scrap_count": 0, "_rest": total - startup, "_share": share})
    counts = pd.DataFrame(rows)
    counts["scrap_count"] = counts["startup_scrap_count"] + rng.binomial(counts["_rest"], counts["_share"])
    return counts.drop(columns=["_rest", "_share"])


def _scrap_share(asset_class: str, story_line: bool, shift_date: object, stories: StoryConfig) -> float:
    if not (story_line and asset_class == COOLANT_CLASS):
        return BASE_SCRAP_SHARE
    day = np.array([pd.Timestamp(shift_date).dayofyear])
    coolant = COOLANT_BASE_C + coolant_rise(day, True, stories.coolant_summer_rise)[0]
    return BASE_SCRAP_SHARE + stories.scrap_share_per_degree * max(0.0, coolant - COOLANT_SCRAP_THRESHOLD)
