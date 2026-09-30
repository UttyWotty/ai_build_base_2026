"""Converts the truth's naive UTC timestamps into the naive local wall-clock times that site systems print.

The offset changes with daylight saving, and the wall-clock value alone no longer says which offset applied;
that loss of information is the MES and CMMS timestamp trap.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.data_pipeline.synthetic.reference import SITES

UTC = "UTC"
TIMEZONES = {site.site_id: site.timezone for site in SITES}


def to_local(utc: pd.Series, site_ids: pd.Series) -> pd.Series:
    """Naive local times for naive UTC timestamps, each in its own site's time zone."""
    result = pd.Series(pd.NaT, index=utc.index, dtype="datetime64[ns]")
    for site_id, zone in TIMEZONES.items():
        mask = (site_ids == site_id).to_numpy()
        if mask.any():
            result[mask] = utc[mask].dt.tz_localize(UTC).dt.tz_convert(zone).dt.tz_localize(None).to_numpy()
    return result
