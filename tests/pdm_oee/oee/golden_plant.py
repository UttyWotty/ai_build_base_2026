"""A hand-built plant for golden OEE tests: two assets, two shifts, and every kind of stop.

Asset A1, shift S1 (00:00-08:00): a 30-minute break, a 60-minute breakdown, a 40-minute changeover, three 2-minute
small stops, a 10-minute blocked stop, and a 60-minute breakdown from 07:30 that runs 30 minutes into S2.
A1 made 100 parts in S1 (5 scrap, 2 at startup) and 200 in S2; A2 ran all of S1 and made 200. Ideal cycle is 120 s.
"""
from __future__ import annotations

import pandas as pd

DAY = "2026-01-05"
IDEAL_CYCLE_S = 120.0
NAMEPLATE_CYCLE_S = 100.0


def at(clock: str) -> pd.Timestamp:
    return pd.Timestamp(f"{DAY} {clock}")


def _states(asset_id: str, rows: list[tuple[str, str, str | None]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["start", "end", "reason"])
    running = frame["reason"].isna()
    planned = frame["reason"] == "scheduled_break"
    return pd.DataFrame({"asset_id": asset_id, "start_at": frame["start"].map(at), "end_at": frame["end"].map(at),
                         "reason": frame["reason"],
                         "state": ["running" if r else "planned_stop" if p else "unplanned_stop" for r, p in zip(running, planned)]})


A1_STATES = [("00:00", "01:00", None), ("01:00", "02:00", "equipment_failure"), ("02:00", "02:40", "changeover"),
             ("02:40", "04:00", None), ("04:00", "04:30", "scheduled_break"), ("04:30", "04:32", "adjustment"),
             ("04:32", "05:00", None), ("05:00", "05:02", "adjustment"), ("05:02", "05:10", None),
             ("05:10", "05:12", "material_starved"), ("05:12", "06:00", None), ("06:00", "06:10", "output_blocked"),
             ("06:10", "07:30", None), ("07:30", "08:30", "equipment_failure"), ("08:30", "16:00", None)]
A2_STATES = [("00:00", "16:00", None)]


def tables() -> dict[str, pd.DataFrame]:
    """The golden plant's conformed tables."""
    assets = pd.DataFrame({"asset_id": ["A1", "A2"], "site_id": "S", "line_id": "S-L1", "asset_class": "cnc_machining_centre",
                           "nameplate_cycle_s": NAMEPLATE_CYCLE_S})
    shifts = pd.DataFrame({"shift_id": ["S1", "S2"], "site_id": "S", "shift_date": pd.Timestamp(DAY).date(),
                           "start_at": [at("00:00"), at("08:00")], "end_at": [at("08:00"), at("16:00")]})
    states = pd.concat([_states("A1", A1_STATES), _states("A2", A2_STATES)], ignore_index=True)
    counts = pd.DataFrame({"asset_id": ["A1", "A1", "A2"], "shift_id": ["S1", "S2", "S1"], "product_id": "P",
                           "order_id": "O", "total_count": [100, 200, 200], "scrap_count": [5, 0, 0],
                           "startup_scrap_count": [2, 0, 0]})
    routings = pd.DataFrame({"product_id": ["P"], "asset_class": ["cnc_machining_centre"], "ideal_cycle_s": [IDEAL_CYCLE_S]})
    return {"asset": assets, "shift": shifts, "machine_state": states, "production_count": counts, "routing": routings}
