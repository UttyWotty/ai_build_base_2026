"""Converts naive local wall-clock times to naive UTC, including the hour that repeats when daylight saving ends.

For rows in their recorded order, a repeated local time takes whichever of its two UTC readings keeps time moving
forward. Unordered times in that hour take the earlier reading; the gap hour in spring cannot occur in real records.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

UTC = "UTC"


def _readings(local: pd.Series, zone: str) -> tuple[np.ndarray, np.ndarray]:
    """The UTC reading of each local time if it was summer time, and if it was standard time."""
    as_summer = local.dt.tz_localize(zone, ambiguous=True).dt.tz_convert(UTC).dt.tz_localize(None).to_numpy()
    as_standard = local.dt.tz_localize(zone, ambiguous=False).dt.tz_convert(UTC).dt.tz_localize(None).to_numpy()
    return as_summer, as_standard


def localize(local: pd.Series, zone: str) -> pd.Series:
    """UTC for local times with no order to go by: a repeated hour is read as its first occurrence."""
    as_summer, _ = _readings(local, zone)
    return pd.Series(as_summer, index=local.index)


def localize_ordered(local: pd.Series, zone: str) -> pd.Series:
    """UTC for local times given in recorded order: each repeated time takes the reading that does not go back in time."""
    as_summer, as_standard = _readings(local, zone)
    result = as_summer.copy()
    for index in np.flatnonzero(as_summer != as_standard):
        previous = result[index - 1] if index else as_summer[index]
        result[index] = as_summer[index] if as_summer[index] >= previous else as_standard[index]
    return pd.Series(result, index=local.index)
