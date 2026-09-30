"""Minute-by-minute state of every asset: running, or stopped with a governed planned or loss reason.

Layers are written in order so later ones win: no production outside shifts, running in shifts, breaks, changeovers,
short operational stops, preventive windows, and finally breakdowns, which override everything until restored.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.core.loss_model import LossTaxonomy
from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.reference import (
    ADJUSTMENT_MINUTES,
    ADJUSTMENTS_PER_SHIFT,
    BREAK_MINUTES,
    BREAK_OFFSET_MINUTES,
    CHANGEOVER_MINUTES,
    EXTERNAL_STOP_MINUTES,
    EXTERNAL_STOPS_PER_SHIFT,
    SMALL_STOP_MINUTES,
    SMALL_STOPS_PER_HOUR,
    TOOL_CHANGE_MINUTES,
    TOOL_CHANGES_PER_SHIFT,
)

RUNNING = "running"
RUNNING_CODE = 0
MINUTES_PER_HOUR = 60
CNC_CLASS = "cnc_machining_centre"
EXTERNAL_CLASSES = frozenset({"hydraulic_press", "conveyor_drive"})
EXTERNAL_REASONS = ("material_starved", "output_blocked", "no_operator")
SMALL_STOP_REASONS = ("adjustment", "material_starved")


@dataclass(frozen=True)
class StateCodes:
    """Code 0 is running; every governed stop reason gets its own code."""

    names: tuple[str, ...]

    def code(self, name: str) -> int:
        return self.names.index(name)


def state_codes(losses: LossTaxonomy) -> StateCodes:
    return StateCodes((RUNNING, *losses.planned_stop_reasons, *losses.loss_reasons))


def build_minute_states(assets: pd.DataFrame, shifts: pd.DataFrame, line_shifts: pd.DataFrame, preventive: pd.DataFrame,
                        failures: pd.DataFrame, codes: StateCodes, stories: StoryConfig, horizon: int,
                        rng: np.random.Generator) -> dict[str, np.ndarray]:
    """One int8 array of state codes per asset, one entry per minute of the horizon."""
    result = {}
    for asset in assets.itertuples():
        states = np.full(horizon, codes.code("no_production_scheduled"), dtype=np.int8)
        site_shifts = shifts[shifts["site_id"] == asset.site_id]
        changeovers = set(line_shifts.loc[(line_shifts["line_id"] == asset.line_id) & line_shifts["changeover"], "shift_id"])
        small_rate = stories.small_stops_per_hour if asset.asset_id == stories.small_stop_asset_id else SMALL_STOPS_PER_HOUR
        for shift in site_shifts.itertuples():
            _fill_shift(states, shift, shift.shift_id in changeovers, asset.asset_class, small_rate, codes, rng)
        for window in preventive[preventive["asset_id"] == asset.asset_id].itertuples():
            states[window.start_minute:window.end_minute] = codes.code("planned_maintenance")
        if len(failures):
            for failure in failures[failures["asset_id"] == asset.asset_id].itertuples():
                states[failure.failed_minute:failure.restored_minute] = codes.code("equipment_failure")
        result[asset.asset_id] = states
    return result


def _fill_shift(states: np.ndarray, shift: object, changeover: bool, asset_class: str, small_rate: float,
                codes: StateCodes, rng: np.random.Generator) -> None:
    start, end = shift.start_minute, shift.end_minute
    states[start:end] = RUNNING_CODE
    states[start + BREAK_OFFSET_MINUTES:start + BREAK_OFFSET_MINUTES + BREAK_MINUTES] = codes.code("scheduled_break")
    if changeover:
        states[start:start + int(rng.integers(CHANGEOVER_MINUTES[0], CHANGEOVER_MINUTES[1] + 1))] = codes.code("changeover")
    if asset_class == CNC_CLASS:
        _stops(states, start, end, rng.poisson(TOOL_CHANGES_PER_SHIFT), TOOL_CHANGE_MINUTES, ("tool_change",), codes, rng)
    _stops(states, start, end, rng.poisson(ADJUSTMENTS_PER_SHIFT), ADJUSTMENT_MINUTES, ("adjustment",), codes, rng)
    if asset_class in EXTERNAL_CLASSES:
        _stops(states, start, end, rng.poisson(EXTERNAL_STOPS_PER_SHIFT), EXTERNAL_STOP_MINUTES, EXTERNAL_REASONS, codes, rng)
    hours = (end - start) / MINUTES_PER_HOUR
    _stops(states, start, end, rng.poisson(small_rate * hours), SMALL_STOP_MINUTES, SMALL_STOP_REASONS, codes, rng)


def _stops(states: np.ndarray, start: int, end: int, count: int, minutes: tuple[int, int], reasons: tuple[str, ...],
           codes: StateCodes, rng: np.random.Generator) -> None:
    """Place `count` stops at random running moments of the shift; they only replace running minutes."""
    for _ in range(int(count)):
        length = int(rng.integers(minutes[0], minutes[1] + 1))
        begin = int(rng.integers(start, max(start + 1, end - length)))
        window = states[begin:begin + length]
        window[window == RUNNING_CODE] = codes.code(str(rng.choice(reasons)))
