"""Conforms MES part counters into counts per asset and shift.

Counters are cumulative. A shift's count is the rise since the previous reading, or the reading itself when the total
counter went down, because counters only reset at a shift start. The go-live snapshot rows (no order) are the baseline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.source_layout import (
    MES_CALENDAR,
    MES_COUNTS,
    Sources,
)

COUNTERS = (("CUM_TOTAL", "total_count"), ("CUM_STARTUP_SCRAP", "startup_scrap_count"), ("CUM_SCRAP", "scrap_count"))


def conform_counts(sources: Sources, assets: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    counts = sources[MES_COUNTS].sort_values(["WORKCENTER", "SHIFT_END_LOCAL"]).reset_index(drop=True)
    first = counts.groupby("WORKCENTER").cumcount() == 0
    reset = counts["CUM_TOTAL"] < counts.groupby("WORKCENTER")["CUM_TOTAL"].shift()
    if (counts.loc[first, "ORDER_NO"].fillna("") != "").any():
        raise ConformError(f"{MES_COUNTS}: a workcenter's first reading must be its go-live snapshot (no order)")
    result = pd.DataFrame({"WORKCENTER": counts["WORKCENTER"], "SHIFT_END_LOCAL": pd.to_datetime(counts["SHIFT_END_LOCAL"]),
                           "order_id": counts["ORDER_NO"]})
    for column, name in COUNTERS:
        previous = counts.groupby("WORKCENTER")[column].shift()
        result[name] = np.where(reset, counts[column], counts[column] - previous)
    result = result[~first].merge(assets[["workcenter", "asset_id", "site_id"]], left_on="WORKCENTER", right_on="workcenter")
    calendar = _shift_ends(sources)
    result = result.merge(calendar, on=["site_id", "SHIFT_END_LOCAL"], how="left")
    if result["shift_id"].isna().any():
        raise ConformError(f"{MES_COUNTS}: readings that match no shift end in {MES_CALENDAR}")
    result = result.merge(orders[["order_id", "product_id"]], on="order_id", how="left")
    if result["product_id"].isna().any():
        raise ConformError(f"{MES_COUNTS}: counts on unknown orders")
    for _, name in COUNTERS:
        result[name] = result[name].astype(np.int64)
    return result[["asset_id", "shift_id", "product_id", "order_id", "total_count", "startup_scrap_count", "scrap_count"]]


def _shift_ends(sources: Sources) -> pd.DataFrame:
    calendar = sources[MES_CALENDAR]
    dates = pd.to_datetime(calendar["SHIFT_DATE"]).dt.date
    return pd.DataFrame({"site_id": calendar["SITE"], "SHIFT_END_LOCAL": pd.to_datetime(calendar["END_LOCAL"]),
                         "shift_id": [f"{s}-{d.isoformat()}-{x}" for s, d, x in zip(calendar["SITE"], dates, calendar["SHIFT"])]})
