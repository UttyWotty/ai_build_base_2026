"""Week arithmetic for the simulation horizon.

Week w starts on horizon_start + 7w (a Monday) and ends six days later (a Sunday).
Dates outside the horizon map to week indexes below zero or at or above the week count.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

DAYS_PER_WEEK = 7
LAST_DAY_OFFSET = 6


@dataclass(frozen=True)
class Timeline:
    """The simulated horizon as a start Monday and a number of weeks."""

    start: date
    weeks: int

    def week_start(self, week: int) -> date:
        """Monday of the given week."""
        return self.start + timedelta(days=DAYS_PER_WEEK * week)

    def week_end(self, week: int) -> date:
        """Sunday of the given week."""
        return self.week_start(week) + timedelta(days=LAST_DAY_OFFSET)

    def week_of(self, day: date) -> int:
        """Index of the week containing the date."""
        return (day - self.start).days // DAYS_PER_WEEK

    @property
    def end(self) -> date:
        """Last day of the horizon; events after it have not happened yet."""
        return self.week_end(self.weeks - 1)


def offsets_to_dates(start: date, offsets: pd.Series) -> pd.Series:
    """Convert integer day offsets (nullable) to Python dates, with None for missing values."""
    stamps = pd.Timestamp(start) + pd.to_timedelta(offsets.astype("Float64"), unit="D")
    return stamps.dt.date.astype(object).where(offsets.notna(), None)
