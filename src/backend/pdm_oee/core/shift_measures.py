"""Computes every asset-and-shift measure in measures.yaml from state intervals, counts, and ideal cycle times.

State intervals are split at shift boundaries; a stop is small when its whole recorded duration is shorter than the
run_time measure's threshold, even if it crosses a shift boundary. Asset-shifts with no count row produced nothing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog

SECONDS_PER_MINUTE = 60.0
THRESHOLD_PARAMETER = "small_stop_threshold_minutes"
RUN_TIME_MEASURE = "run_time"
PLANNED, LONG_LOSS, SHORT_LOSS = "planned", "long_loss", "short_loss"


def small_stop_threshold(catalog: PlantCatalog) -> float:
    """The run_time measure's small-stop threshold, in minutes."""
    return catalog.measures[RUN_TIME_MEASURE].parameters[THRESHOLD_PARAMETER]


def split_by_shift(states: pd.DataFrame, shifts: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    """Every state interval's minutes inside each shift of its asset's site: asset_id, shift_id, reason, minutes, full_minutes."""
    pieces = []
    site_of = assets.set_index("asset_id")["site_id"]
    for asset_id, rows in states.groupby("asset_id", sort=True):
        site_shifts = shifts[shifts["site_id"] == site_of[asset_id]].sort_values("start_at")
        starts, ends = site_shifts["start_at"].to_numpy(), site_shifts["end_at"].to_numpy()
        begin, end = rows["start_at"].to_numpy(), rows["end_at"].to_numpy()
        first = np.searchsorted(ends, begin, side="right")
        last = np.searchsorted(starts, end, side="left")
        repeat = np.maximum(last - first, 0)
        which = np.repeat(np.arange(len(rows)), repeat)
        offsets = np.arange(repeat.sum()) - np.repeat(np.cumsum(repeat) - repeat, repeat)
        shift_index = np.repeat(first, repeat) + offsets
        overlap = (np.minimum(end[which], ends[shift_index]) - np.maximum(begin[which], starts[shift_index])) / np.timedelta64(1, "m")
        pieces.append(pd.DataFrame({"asset_id": asset_id, "shift_id": site_shifts["shift_id"].to_numpy()[shift_index],
                                    "reason": rows["reason"].to_numpy()[which], "minutes": overlap,
                                    "full_minutes": (end[which] - begin[which]) / np.timedelta64(1, "m")}))
    return pd.concat(pieces, ignore_index=True)


def classify_stops(pieces: pd.DataFrame, catalog: PlantCatalog) -> pd.Series:
    """planned, long_loss, short_loss, or None (running) for each piece."""
    threshold = small_stop_threshold(catalog)
    planned = pieces["reason"].isin(list(catalog.losses.planned_stop_reasons))
    loss = pieces["reason"].isin(list(catalog.losses.loss_reasons))
    kind = np.select([planned, loss & (pieces["full_minutes"] >= threshold), loss], [PLANNED, LONG_LOSS, SHORT_LOSS], None)
    return pd.Series(kind, index=pieces.index)


def shift_measures(states: pd.DataFrame, shifts: pd.DataFrame, assets: pd.DataFrame, counts: pd.DataFrame,
                   routings: pd.DataFrame, catalog: PlantCatalog) -> pd.DataFrame:
    """One row per asset and shift of its site, with every asset_shift measure as a column."""
    pieces = split_by_shift(states, shifts, assets)
    pieces["kind"] = classify_stops(pieces, catalog)
    minutes = pieces.pivot_table(index=["asset_id", "shift_id"], columns="kind", values="minutes", aggfunc="sum", fill_value=0.0)
    grid = assets[["asset_id", "site_id", "asset_class", "nameplate_cycle_s"]].merge(
        shifts[["shift_id", "site_id", "start_at", "end_at"]], on="site_id")
    grid = grid.merge(minutes.reset_index(), on=["asset_id", "shift_id"], how="left")
    for kind in (PLANNED, LONG_LOSS, SHORT_LOSS):
        grid[kind] = grid[kind].fillna(0.0) if kind in grid else 0.0
    grid["calendar_time"] = (grid["end_at"] - grid["start_at"]) / pd.Timedelta(minutes=1)
    grid["planned_production_time"] = grid["calendar_time"] - grid[PLANNED]
    grid["run_time"] = grid["planned_production_time"] - grid[LONG_LOSS]
    grid["run_time_all_stops"] = grid["run_time"] - grid[SHORT_LOSS]
    grid = grid.merge(counts[["asset_id", "shift_id", "product_id", "total_count", "scrap_count", "startup_scrap_count"]],
                      on=["asset_id", "shift_id"], how="left")
    grid = grid.merge(routings, on=["product_id", "asset_class"], how="left")
    for column in ("total_count", "scrap_count", "startup_scrap_count", "ideal_cycle_s"):
        grid[column] = grid[column].fillna(0)
    ideal_minutes = grid["ideal_cycle_s"] / SECONDS_PER_MINUTE
    grid["good_count"] = grid["total_count"] - grid["scrap_count"]
    grid["ideal_run_time"] = grid["total_count"] * ideal_minutes
    grid["valuable_operating_time"] = grid["good_count"] * ideal_minutes
    grid["nameplate_valuable_time"] = grid["good_count"] * grid["nameplate_cycle_s"] / SECONDS_PER_MINUTE
    grid["small_stop_time"] = grid[SHORT_LOSS]
    return grid.drop(columns=[PLANNED, LONG_LOSS, SHORT_LOSS])
