"""Failure processes: for every asset and failure mode, onsets of wear and the failures and repairs that follow.

Predictable modes wear from onset to failure over their P-F interval; unpredictable ones fail without warning.
The two failure stories are placed exactly, and natural events that would overlap them are dropped.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.core.plant_model import FailureMode, PlantModel
from pdm_oee.data_pipeline.synthetic.calendar import MINUTES_PER_DAY
from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.errors import GenerationError
from pdm_oee.data_pipeline.synthetic.reference import (
    BASELINE_WINDOW_DAYS,
    MEAN_DAYS_TO_ONSET,
    PF_VARIATION,
    REPAIR_VARIATION,
    RESPONSE_HOURS,
)

MINUTES_PER_HOUR = 60
STORY_FAILURE_MINUTE_OF_DAY = 10 * MINUTES_PER_HOUR
BEARING_MODE = "spindle_bearing_wear"
PUMP_MODE = "hydraulic_pump_wear"


@dataclass(frozen=True)
class Degradation:
    """One wear-to-failure episode; failed_minute may lie beyond the horizon (still degrading at the end)."""

    asset_id: str
    component: str
    failure_mode: str
    onset_minute: int | None
    failed_minute: int
    restored_minute: int
    story: bool


def simulate_failures(assets: pd.DataFrame, plant: PlantModel, stories: StoryConfig, horizon: int,
                      rng: np.random.Generator) -> list[Degradation]:
    """Every degradation episode that starts inside the horizon, stories included."""
    placed = _story_events(assets, plant, stories, horizon)
    events = list(placed)
    for asset in assets.itertuples():
        for mode in plant.asset_classes[asset.asset_class].failure_modes.values():
            natural = _natural(asset.asset_id, mode, horizon, rng)
            story = [p for p in placed if p.asset_id == asset.asset_id and p.failure_mode == mode.id]
            events += [e for e in natural if not any(_overlaps(e, s) for s in story)]
    return _one_repair_at_a_time(sorted(events, key=lambda e: (e.failed_minute, e.asset_id, e.failure_mode)))


def _one_repair_at_a_time(events: list[Degradation]) -> list[Degradation]:
    """Drop failures that would start while the same asset is still down: the open repair would find and fix them."""
    kept, restored_until = [], {}
    for event in events:
        if event.story or event.failed_minute > restored_until.get(event.asset_id, -1):
            kept.append(event)
            restored_until[event.asset_id] = max(restored_until.get(event.asset_id, -1), event.restored_minute)
    return kept


def _natural(asset_id: str, mode: FailureMode, horizon: int, rng: np.random.Generator) -> list[Degradation]:
    events, clock = [], BASELINE_WINDOW_DAYS * MINUTES_PER_DAY
    mean = MEAN_DAYS_TO_ONSET[mode.id] * MINUTES_PER_DAY
    while clock < horizon:
        start = clock + int(rng.exponential(mean))
        if mode.predictable:
            failed = start + int(mode.pf_interval_days * MINUTES_PER_DAY * rng.uniform(*PF_VARIATION))
        else:
            failed = start
        if start >= horizon:
            break
        restored = failed + _repair_minutes(mode, rng)
        events.append(Degradation(asset_id, mode.component, mode.id, start if mode.predictable else None, failed, restored, False))
        clock = restored + (BASELINE_WINDOW_DAYS * MINUTES_PER_DAY if mode.predictable else 0)
    return events


def _repair_minutes(mode: FailureMode, rng: np.random.Generator) -> int:
    hours = mode.repair_hours * rng.uniform(*REPAIR_VARIATION) + rng.uniform(*RESPONSE_HOURS)
    return int(hours * MINUTES_PER_HOUR)


def _story_events(assets: pd.DataFrame, plant: PlantModel, stories: StoryConfig, horizon: int) -> list[Degradation]:
    events = []
    for asset_id, mode_id, day in ((stories.bearing_asset_id, BEARING_MODE, stories.bearing_failure_day),
                                   (stories.pump_asset_id, PUMP_MODE, stories.pump_failure_day)):
        row = assets[assets["asset_id"] == asset_id]
        modes = plant.asset_classes[row["asset_class"].iloc[0]].failure_modes if len(row) else {}
        if mode_id not in modes:
            raise GenerationError(f"Story asset {asset_id} does not exist or cannot have {mode_id}")
        mode = modes[mode_id]
        failed = day * MINUTES_PER_DAY + STORY_FAILURE_MINUTE_OF_DAY
        onset = failed - int(mode.pf_interval_days * MINUTES_PER_DAY)
        if onset < 0 or failed >= horizon:
            raise GenerationError(f"Story failure of {asset_id} on day {day} does not fit in the horizon")
        restored = failed + int(mode.repair_hours * MINUTES_PER_HOUR)
        events.append(Degradation(asset_id, mode.component, mode_id, onset, failed, restored, True))
    return events


def _overlaps(event: Degradation, story: Degradation) -> bool:
    margin = BASELINE_WINDOW_DAYS * MINUTES_PER_DAY
    start = event.onset_minute if event.onset_minute is not None else event.failed_minute
    return start < story.restored_minute + margin and event.restored_minute + margin > (story.onset_minute or 0)


def failure_frame(events: list[Degradation], horizon: int) -> pd.DataFrame:
    """Failures that happened inside the horizon, as a table."""
    rows = [{"asset_id": e.asset_id, "component": e.component, "failure_mode": e.failure_mode,
             "onset_minute": e.onset_minute, "failed_minute": e.failed_minute,
             "restored_minute": min(e.restored_minute, horizon), "story": e.story}
            for e in events if e.failed_minute < horizon]
    return pd.DataFrame(rows)
