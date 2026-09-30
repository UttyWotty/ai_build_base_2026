"""Cumulative completion: the date on which running quantity first reaches the ordered quantity.

Both PO receipt rollups and sales delivery rollups use this rule, so it is implemented once.
Events on the same date are ordered by a tie-break id so the result is deterministic.
"""
from __future__ import annotations

import pandas as pd


def completion_dates(
    events: pd.DataFrame, key: str, date_column: str, qty_column: str, tie_break: str, ordered: pd.Series
) -> pd.Series:
    """For each key in `ordered` (indexed by key), the event date at which cumulative qty reaches the ordered qty.

    Keys that never complete map to None.
    """
    ordered_events = events.sort_values([key, date_column, tie_break], kind="mergesort")
    cumulative = ordered_events.groupby(key)[qty_column].cumsum()
    target = ordered_events[key].map(ordered)
    reached = ordered_events[cumulative >= target]
    first = reached.groupby(key)[date_column].first()
    return pd.Series(ordered.index.map(first), index=ordered.index, dtype=object).where(
        ordered.index.isin(first.index), None
    )
