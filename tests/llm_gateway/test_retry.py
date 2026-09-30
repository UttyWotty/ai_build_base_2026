"""Tests for the retry policy: which failures are transient and how the backoff grows.

Rate limits, server errors, and network errors are retried; other client errors are not.
Delays double from the base and stop at the cap.
"""
from __future__ import annotations

from llm_gateway.retry import RetryPolicy, is_transient


def test_transient_failures() -> None:
    assert is_transient(429) and is_transient(500) and is_transient(503) and is_transient(None)
    assert not is_transient(400) and not is_transient(403) and not is_transient(404)


def test_backoff_doubles_and_is_capped() -> None:
    policy = RetryPolicy(retries=5, base_delay_seconds=2.0, max_delay_seconds=10.0)
    assert [policy.delay_before(n) for n in range(1, 6)] == [2.0, 4.0, 8.0, 10.0, 10.0]
