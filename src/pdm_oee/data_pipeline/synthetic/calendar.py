"""The simulation clock: minutes since the horizon start in UTC, and each site's production shifts on that clock.

Shifts start at local times, so daylight-saving changes move them in UTC; that is exactly what the MES trap relies on.
Weekends and holidays have no shifts; the shift table is the only place local time is converted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from pdm_oee.data_pipeline.synthetic.reference import (
    HOLIDAYS,
    PRODUCTION_WEEKDAYS,
    SHIFT_HOURS,
    SHIFT_START_HOURS,
    SiteSpec,
)

MINUTES_PER_DAY = 1440
SECONDS_PER_MINUTE = 60
SHIFT_LETTERS = "ABC"


@dataclass(frozen=True)
class Clock:
    """The horizon: its UTC start and its length in minutes."""

    start: datetime
    minutes: int

    def to_utc(self, minute: int) -> datetime:
        return self.start + timedelta(minutes=int(minute))

    def minute_of(self, moment: datetime) -> int:
        return int((moment - self.start).total_seconds() // SECONDS_PER_MINUTE)


def make_clock(horizon_start: date, weeks: int) -> Clock:
    """Midnight UTC on the first day, for the given number of weeks."""
    start = datetime.combine(horizon_start, time(0), tzinfo=timezone.utc)
    return Clock(start=start, minutes=weeks * 7 * MINUTES_PER_DAY)


def shift_table(site: SiteSpec, clock: Clock) -> pd.DataFrame:
    """Every production shift at the site that lies fully inside the horizon, in time order."""
    zone = ZoneInfo(site.timezone)
    rows = []
    first = clock.start.date() - timedelta(days=1)
    for offset in range(clock.minutes // MINUTES_PER_DAY + 2):
        day = first + timedelta(days=offset)
        if day.weekday() >= PRODUCTION_WEEKDAYS or (day.month, day.day) in HOLIDAYS:
            continue
        for letter, hour in zip(SHIFT_LETTERS, SHIFT_START_HOURS):
            start_local = datetime.combine(day, time(hour), tzinfo=zone)
            end_local = start_local + timedelta(hours=SHIFT_HOURS)
            start, end = clock.minute_of(start_local.astimezone(timezone.utc)), clock.minute_of(end_local.astimezone(timezone.utc))
            if start >= 0 and end <= clock.minutes:
                rows.append({"shift_id": f"{site.site_id}-{day.isoformat()}-{letter}", "site_id": site.site_id,
                             "shift_date": day, "shift_letter": letter, "start_minute": start, "end_minute": end})
    return pd.DataFrame(rows)
