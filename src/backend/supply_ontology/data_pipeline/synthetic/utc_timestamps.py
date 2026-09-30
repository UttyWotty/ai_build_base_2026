"""Converts local event times (a date, an hour, and a time zone) into UTC ISO-8601 strings as a TMS or portal stores them.

This reproduces a common source trap: the UTC calendar date can differ from the local date for time zones far from UTC.
Conversion is vectorized per time zone; hours are kept away from daylight-saving transitions by the generators.
"""
from __future__ import annotations

import pandas as pd

UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
UTC_ZONE = "UTC"


def local_to_utc_strings(days: pd.Series, hours: pd.Series, zones: pd.Series) -> pd.Series:
    """Return UTC ISO strings for each (local date, hour, zone); rows with a missing date yield None."""
    result = pd.Series([None] * len(days), index=days.index, dtype=object)
    present = days.notna()
    for zone in sorted(zones[present].unique()):
        mask = present & (zones == zone)
        local = pd.to_datetime(days[mask].astype(str)) + pd.to_timedelta(hours[mask].astype(int), unit="h")
        result[mask] = local.dt.tz_localize(zone).dt.tz_convert(UTC_ZONE).dt.strftime(UTC_FORMAT)
    return result
