"""Tests for the closed loop: approved decisions change stock and queues, outcomes settle only once the clock passes
the real outcome, and the feed tells the story.

A transfer leaves the sister shelf at once and reaches the alert's site when promised; other alerts stop competing for it.
Outcomes stay pending until the failure or the end of the warning window.
"""
from __future__ import annotations

from datetime import timedelta

from copilot.core.decision_events import decision_events
from copilot.core.decisions import Decision, apply_decisions
from copilot.core.impact_model import Claim
from copilot.core.outcomes import OutcomeStatus, decision_outcome
from tests.copilot.fixtures import T0, position
from tests.copilot.test_value_backtest import report

TRANSFER = Decision("PR-1", "AL-2", "A-L1-01", "A", "SP-1", "transfer", "B", T0, T0 + timedelta(hours=48), 650.0, 1)
CLAIMS = (Claim("AL-1", "A-L3-01", T0 - timedelta(days=1)), Claim("AL-2", "A-L1-01", T0 + timedelta(days=3)))


def test_a_transfer_empties_the_sister_and_arrives_later_for_its_own_alert() -> None:
    sister = apply_decisions(position("B", 1), "SP-1", [TRANSFER], T0 + timedelta(hours=1))
    assert sister.on_hand == 0
    own = apply_decisions(position("A", 1, CLAIMS), "SP-1", [TRANSFER], T0 + timedelta(hours=1), for_alert="AL-2")
    assert [o.po_id for o in own.open_orders] == ["DEC-PR-1"]
    other = apply_decisions(position("A", 1, CLAIMS), "SP-1", [TRANSFER], T0 + timedelta(hours=1), for_alert="AL-1")
    assert [c.alert_id for c in other.claims] == ["AL-1"] and other.open_orders == ()


def test_decisions_apply_only_from_their_moment_and_arrivals_are_reserved() -> None:
    before = apply_decisions(position("B", 1), "SP-1", [TRANSFER], T0 - timedelta(hours=1))
    assert before.on_hand == 1
    arrived = apply_decisions(position("A", 0, CLAIMS), "SP-1", [TRANSFER], T0 + timedelta(hours=49), for_alert="AL-1")
    assert arrived.on_hand == 0
    mine = apply_decisions(position("A", 0, CLAIMS), "SP-1", [TRANSFER], T0 + timedelta(hours=49), for_alert="AL-2")
    assert mine.on_hand == 1


def test_outcomes_settle_only_after_the_failure_or_the_window() -> None:
    r = report()
    failed = T0 + timedelta(hours=30)
    assert decision_outcome(TRANSFER, r, failed, 6.0, T0 + timedelta(hours=10)).status is OutcomeStatus.PENDING
    settled = decision_outcome(TRANSFER, r, failed, 6.0, T0 + timedelta(hours=31))
    assert settled.status is OutcomeStatus.FAILED and settled.hours_saved == 144.0
    quiet = decision_outcome(TRANSFER, r, None, 6.0, T0 + timedelta(days=7))
    assert quiet.status is OutcomeStatus.NO_FAILURE and quiet.with_plan.extra_cost_usd == 650.0


def test_the_feed_tells_the_decision_story() -> None:
    settled = decision_outcome(TRANSFER, report(), T0 + timedelta(hours=30), 6.0, T0 + timedelta(hours=31))
    events = decision_events(TRANSFER, settled)
    assert [e.kind for e in events] == ["decision", "decision_arrival", "outcome"]
    assert "air transfer from B" in events[0].title and "instead of 172.0 h" in events[2].title
