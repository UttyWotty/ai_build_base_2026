"""Retry policy for model calls: which failures are worth retrying, and how long to wait before each attempt.

Rate limits (429) and server errors (5xx) are transient on shared or free-tier endpoints; other client errors are not.
Delays grow exponentially from a base and are capped, so a burst of rate limits backs off without stalling a demo.
"""
from __future__ import annotations

from dataclasses import dataclass

RATE_LIMITED = 429
FIRST_SERVER_ERROR = 500
LAST_SERVER_ERROR = 599


@dataclass(frozen=True)
class RetryPolicy:
    """Attempt count and backoff shape."""

    # Retries after the first attempt.
    retries: int = 4
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 30.0

    def delay_before(self, retry_number: int) -> float:
        """Seconds to wait before retry number 1, 2, ..."""
        return min(self.base_delay_seconds * 2 ** (retry_number - 1), self.max_delay_seconds)


def is_transient(status_code: int | None) -> bool:
    """True for rate limits and server errors, and for failures with no status (network errors)."""
    if status_code is None:
        return True
    return status_code == RATE_LIMITED or FIRST_SERVER_ERROR <= status_code <= LAST_SERVER_ERROR
