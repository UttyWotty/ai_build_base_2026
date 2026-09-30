"""Derived attributes of inventory snapshots: on-hand value and trailing average daily cost of goods shipped.

COGS is outbound shipped quantity at standard cost, attributed to the shipping plant on the local ship date.
The trailing window covers the `window_days` days ending on (and including) each snapshot date.
"""
from __future__ import annotations

import pandas as pd

KEYS = ["plant_id", "part_id"]


def add_inventory_values(
    snapshots: pd.DataFrame, part: pd.DataFrame, shipment_lines: pd.DataFrame,
    shipment: pd.DataFrame, sales_lines: pd.DataFrame, window_days: int,
) -> pd.DataFrame:
    """Add on_hand_value_usd and trailing_daily_cogs_usd."""
    cost = part.set_index("part_id")["standard_cost_usd"]
    frame = snapshots.copy()
    frame["on_hand_value_usd"] = frame["qty_on_hand"] * frame["part_id"].map(cost).to_numpy()
    shipped = shipment_lines.merge(shipment[["shipment_id", "ship_date"]], on="shipment_id").merge(
        sales_lines[["so_line_id", *KEYS]], on="so_line_id"
    )
    shipped["cogs_usd"] = shipped["qty_shipped"] * shipped["part_id"].map(cost).to_numpy()
    shipped["day"] = pd.to_datetime(shipped["ship_date"])
    snapshot_days = pd.to_datetime(frame["snapshot_date"])
    calendar = pd.date_range(snapshot_days.min() - pd.Timedelta(days=window_days), snapshot_days.max(), freq="D")
    daily = shipped.pivot_table(index="day", columns=KEYS, values="cogs_usd", aggfunc="sum").reindex(calendar, fill_value=0.0)
    trailing = daily.fillna(0.0).rolling(window_days, min_periods=1).sum() / window_days
    lookup = trailing.stack(KEYS, future_stack=True)
    keys = pd.MultiIndex.from_arrays([snapshot_days, frame["plant_id"], frame["part_id"]])
    frame["trailing_daily_cogs_usd"] = lookup.reindex(keys).fillna(0.0).to_numpy()
    return frame
