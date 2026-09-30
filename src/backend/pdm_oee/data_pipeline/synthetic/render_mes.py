"""Renders the MES: state intervals in local time with site codes, cumulative part counters, reason codes, and shifts.

States carry a per-workcenter sequence number, the only way to order rows around a daylight-saving fall-back.
Counters are cumulative, start with a go-live snapshot row, and occasionally reset to zero at a shift start,
at least MIN_SHIFTS_BETWEEN_RESETS apart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.loss_model import LossTaxonomy
from pdm_oee.data_pipeline.synthetic.local_time import to_local
from pdm_oee.data_pipeline.synthetic.reference import SITES
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile

RESET_SHARE = 0.02
MIN_SHIFTS_BETWEEN_RESETS = 60
COUNTER_START = (10_000, 90_000)
EMPTY_CODE = ""


def render_mes(tables: dict[str, pd.DataFrame], losses: LossTaxonomy, horizon_start: pd.Timestamp,
               rng: np.random.Generator) -> list[SourceFile]:
    assets = tables["asset"].set_index("asset_id")
    return [SourceFile("mes/states.parquet", _states(tables["machine_state"], assets), FileFormat.PARQUET),
            SourceFile("mes/counts.parquet", _counts(tables, assets, horizon_start, rng), FileFormat.PARQUET),
            SourceFile("mes/reason_codes.xlsx", _reason_codes(losses), FileFormat.XLSX),
            SourceFile("mes/shift_calendar.xlsx", _calendar(tables["shift"]), FileFormat.XLSX)]


def _states(states: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    site = states["asset_id"].map(assets["site_id"])
    state_codes = {s.site_id: s.state_codes for s in SITES}
    reason_codes = {s.site_id: s.reason_codes for s in SITES}
    frame = pd.DataFrame({
        "WORKCENTER": states["asset_id"].map(assets["workcenter"]),
        "START_LOCAL": to_local(states["start_at"], site), "END_LOCAL": to_local(states["end_at"], site),
        "STATE": [state_codes[s][x] for s, x in zip(site, states["state"])],
        "REASON": [EMPTY_CODE if r is None else reason_codes[s][r] for s, r in zip(site, states["reason"])],
    })
    frame.insert(1, "SEQ", frame.groupby("WORKCENTER").cumcount() + 1)
    return frame


def _counts(tables: dict[str, pd.DataFrame], assets: pd.DataFrame, horizon_start: pd.Timestamp,
            rng: np.random.Generator) -> pd.DataFrame:
    """Cumulative counters per workcenter, preceded by the go-live snapshot row (empty order number)."""
    counts = tables["production_count"].merge(tables["shift"][["shift_id", "end_at"]], on="shift_id").sort_values(["asset_id", "end_at"])
    frames = []
    for asset_id, group in counts.groupby("asset_id", sort=True):
        resets = _reset_points(len(group), rng)
        columns = {}
        for name, column in (("CUM_TOTAL", "total_count"), ("CUM_SCRAP", "scrap_count"), ("CUM_STARTUP_SCRAP", "startup_scrap_count")):
            columns[name] = _cumulative(group[column].to_numpy(), resets, int(rng.integers(*COUNTER_START)))
        site = pd.Series(assets.loc[asset_id, "site_id"], index=group.index)
        workcenter = assets.loc[asset_id, "workcenter"]
        baseline = {name: values[0] - int(group[column].iloc[0]) for (name, values), column in
                    zip(columns.items(), ("total_count", "scrap_count", "startup_scrap_count"))}
        frames.append(pd.DataFrame([{"WORKCENTER": workcenter, "SHIFT_END_LOCAL": to_local(
            pd.Series([horizon_start]), pd.Series([assets.loc[asset_id, "site_id"]])).iloc[0], "ORDER_NO": EMPTY_CODE, **baseline}]))
        frames.append(pd.DataFrame({"WORKCENTER": workcenter,
                                    "SHIFT_END_LOCAL": to_local(group["end_at"], site), "ORDER_NO": group["order_id"],
                                    **columns}))
    return pd.concat(frames, ignore_index=True)


def _reset_points(length: int, rng: np.random.Generator) -> np.ndarray:
    resets, since = np.zeros(length, dtype=bool), 0
    for index in range(length):
        since += 1
        if since >= MIN_SHIFTS_BETWEEN_RESETS and rng.random() < RESET_SHARE:
            resets[index], since = True, 0
    return resets


def _cumulative(values: np.ndarray, resets: np.ndarray, start: int) -> np.ndarray:
    """Running total that restarts from zero at each reset shift (the reset happens at that shift's start)."""
    result, running = np.empty(len(values), dtype=np.int64), start
    for index, value in enumerate(values):
        running = (0 if resets[index] else running) + int(value)
        result[index] = running
    return result


def _reason_codes(losses: LossTaxonomy) -> pd.DataFrame:
    labels = {**{r.id: r.label for r in losses.planned_stop_reasons.values()}, **{r.id: r.label for r in losses.loss_reasons.values()}}
    return pd.DataFrame([{"SITE": s.site_id, "CODE": code, "DESCRIPTION": labels[reason]}
                         for s in SITES for reason, code in s.reason_codes.items()])


def _calendar(shifts: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"SITE": shifts["site_id"], "SHIFT_DATE": shifts["shift_date"], "SHIFT": shifts["shift_letter"],
                         "START_LOCAL": to_local(shifts["start_at"], shifts["site_id"]),
                         "END_LOCAL": to_local(shifts["end_at"], shifts["site_id"]),
                         "BREAK_MINUTES": shifts["planned_break_minutes"]})
