"""Local wall-clock times to UTC across daylight saving, including the repeated hour when it ends.

In recorded order, a repeated time takes the reading that keeps time moving forward; without order, the first reading.
Chicago falls back at 02:00 on 2025-11-02, so 01:00-01:59 happens twice.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.data_pipeline.conform.local_clock import localize, localize_ordered

CHICAGO = "America/Chicago"


def test_ordered_times_through_a_fall_back_keep_moving_forward() -> None:
    local = pd.Series(pd.to_datetime(["2025-11-02 00:50", "2025-11-02 01:40", "2025-11-02 01:10", "2025-11-02 02:05"]))
    utc = localize_ordered(local, CHICAGO)
    assert list(utc.dt.strftime("%H:%M")) == ["05:50", "06:40", "07:10", "08:05"]
    assert utc.is_monotonic_increasing


def test_unordered_repeated_time_reads_as_its_first_occurrence() -> None:
    utc = localize(pd.Series(pd.to_datetime(["2025-11-02 01:30", "2025-07-01 12:00"])), CHICAGO)
    assert list(utc.dt.strftime("%m-%d %H:%M")) == ["11-02 06:30", "07-01 17:00"]
