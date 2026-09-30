"""How soon alerts of a failure mode have turned into failures, learned only from outcomes already in the past.

For an analysis at time t, only alerts whose failure happened before t count, so no future outcome leaks in.
The fastest past lead time gives an earliest plausible failure, used to price a worst case next to the expected one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class AlertOutcome:
    """An alert that was followed by the failure it warned about."""

    failure_mode: str
    raised_at: datetime
    failed_at: datetime

    @property
    def lead_hours(self) -> float:
        return (self.failed_at - self.raised_at).total_seconds() / SECONDS_PER_HOUR


@dataclass(frozen=True)
class LeadStats:
    """Lead times of past alerts of one failure mode."""

    failure_mode: str
    count: int
    fastest_hours: float | None
    median_hours: float | None


def lead_stats(outcomes: list[AlertOutcome], failure_mode: str, as_of: datetime) -> LeadStats:
    """Stats over the mode's alerts whose failure is already in the past at as_of."""
    leads = [o.lead_hours for o in outcomes if o.failure_mode == failure_mode and o.failed_at < as_of]
    if not leads:
        return LeadStats(failure_mode, 0, None, None)
    return LeadStats(failure_mode, len(leads), round(min(leads), 1), round(median(leads), 1))
