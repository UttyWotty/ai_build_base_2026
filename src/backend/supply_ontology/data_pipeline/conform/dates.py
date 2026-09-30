"""Date normalisation helpers for source columns: native dates, UTC timestamp strings, and day-first text.

UTC timestamps are converted to the local calendar date of a given time zone, which is what the ontology stores.
All helpers return object Series of datetime.date values, with None where the source value is missing.
"""
from __future__ import annotations

import pandas as pd

DAY_FIRST_FORMAT = "%d/%m/%Y"


def as_dates(values: pd.Series) -> pd.Series:
    """Convert date-like values (dates, datetimes, ISO strings) to dates; missing values become None."""
    stamps = pd.to_datetime(values)
    return stamps.dt.date.astype(object).where(stamps.notna(), None)


def day_first_dates(values: pd.Series) -> pd.Series:
    """Parse DD/MM/YYYY text into dates."""
    return as_dates(pd.to_datetime(values, format=DAY_FIRST_FORMAT))


def utc_to_local_dates(utc_strings: pd.Series, zones: pd.Series) -> pd.Series:
    """Convert UTC timestamp strings to the local calendar date in each row's time zone."""
    result = pd.Series([None] * len(utc_strings), index=utc_strings.index, dtype=object)
    present = utc_strings.notna()
    stamps = pd.to_datetime(utc_strings[present], utc=True)
    for zone in sorted(zones[present].unique()):
        mask = zones[present] == zone
        result[stamps[mask].index] = stamps[mask].dt.tz_convert(zone).dt.date.to_numpy()
    return result
