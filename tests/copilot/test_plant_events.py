"""Tests for the plant event feed: event titles and severities, covered alerts, and the window that never shows the future.

Rows are hand-built; the feed is sorted newest first and capped.
A failure that is restored after the window shows only its breakdown.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from copilot.core.plant_events import (
    AlertRow,
    FailureRow,
    MovementRow,
    OrderRow,
    Severity,
    build_feed,
)

T0 = datetime(2026, 7, 25, 2, 0)


def test_feed_merges_sources_newest_first_and_stops_at_the_window_end() -> None:
    alerts = [AlertRow("AL-1", "US1-L2-01", "US1", "spindle_bearing_wear", "P2", T0),
              AlertRow("AL-0", "US1-L1-01", "US1", "gearbox_wear", "P2", T0 - timedelta(hours=1), opens_draft=False)]
    failures = [FailureRow("US1-L3-01", "US1", "tool_changer_jam", T0 + timedelta(hours=1), T0 + timedelta(hours=30))]
    movements = [MovementRow("US1", "Bearing set", T0 + timedelta(hours=2), "consumption", -1, "F1", 0),
                 MovementRow("US1", "Bearing set", T0 + timedelta(hours=3), "initial", 2, "initial", 2)]
    orders = [OrderRow("SPO-1", "US1", "Bearing set", "Everline", 1, T0 + timedelta(hours=2), T0 + timedelta(days=14))]
    feed = build_feed(alerts, failures, movements, orders, T0 - timedelta(hours=2), T0 + timedelta(hours=2))
    assert [e.kind for e in feed] == ["spare_used", "spare_ordered", "breakdown", "alert", "alert_covered"]
    assert feed[0].severity is Severity.WARNING and feed[0].title == "Bearing set used at US1, 0 left"
    assert feed[3].alert_id == "AL-1" and "predicted on US1-L2-01" in feed[3].title
    assert "already covered" in feed[4].title


def test_restoration_title_carries_the_downtime() -> None:
    failures = [FailureRow("A", "US1", "main_seal_leak", T0, T0 + timedelta(hours=9, minutes=18))]
    feed = build_feed([], failures, [], [], T0, T0 + timedelta(days=1))
    assert feed[0].title == "A back in production after 9.3 h" and feed[0].severity is Severity.GOOD
