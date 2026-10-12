"""Caps how often the public demo calls Gemini, per visitor and in total, over a sliding window.

The total cap is the hard guarantee that nobody can drain the project's credit; the per-visitor cap keeps one visitor
from using up everyone's share. State is in memory and the clock is passed in, so the rules are pure and testable.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

VISITOR = "visitor"
TOTAL = "total"
NO_SCOPE = ""
SECONDS_PER_MINUTE = 60
# A cap of 0 turns that cap off, for local development and tests.
OFF = 0


@dataclass(frozen=True)
class UsageLimits:
    """Model calls allowed per visitor and in total within one window; 0 disables a cap."""

    per_visitor: int
    total: int
    window: timedelta


@dataclass(frozen=True)
class LimitDecision:
    """Whether a call may go ahead, and if not, which cap stopped it and when to try again."""

    allowed: bool
    scope: str
    retry_after_seconds: int


class UsageLimiter:
    """Sliding-window counters; an allowed call is recorded, a refused one is not."""

    def __init__(self, limits: UsageLimits) -> None:
        self.limits = limits
        self._total: deque[datetime] = deque()
        self._visitors: dict[str, deque[datetime]] = {}

    def check(self, visitor: str, now: datetime) -> LimitDecision:
        start = now - self.limits.window
        _prune(self._total, start)
        for key in list(self._visitors):
            _prune(self._visitors[key], start)
            if not self._visitors[key]:
                del self._visitors[key]
        mine = self._visitors.get(visitor, deque())
        if self.limits.total != OFF and len(self._total) >= self.limits.total:
            return LimitDecision(False, TOTAL, _retry_after(self._total, self.limits.window, now))
        if self.limits.per_visitor != OFF and len(mine) >= self.limits.per_visitor:
            return LimitDecision(False, VISITOR, _retry_after(mine, self.limits.window, now))
        self._total.append(now)
        self._visitors.setdefault(visitor, deque()).append(now)
        return LimitDecision(True, NO_SCOPE, 0)


def _prune(times: deque[datetime], start: datetime) -> None:
    while times and times[0] <= start:
        times.popleft()


def _retry_after(times: deque[datetime], window: timedelta, now: datetime) -> int:
    return max(1, int((times[0] + window - now).total_seconds()))


def limit_message(decision: LimitDecision, limits: UsageLimits) -> str:
    """Plain words for a refused call, with the wait in minutes."""
    minutes = max(1, -(-decision.retry_after_seconds // SECONDS_PER_MINUTE))
    window = int(limits.window.total_seconds() // SECONDS_PER_MINUTE)
    if decision.scope == TOTAL:
        return (f"The live demo has reached its limit of {limits.total} AI runs per {window} minutes, which keeps it "
                f"up for everyone. Try again in about {minutes} minutes.")
    return (f"The live demo allows {limits.per_visitor} AI runs per visitor per {window} minutes, so it stays up for "
            f"everyone. Try again in about {minutes} minutes.")
