"""Tests for the impact rules: the spare queue, open claims, lead history, option pricing, and the recommendation.

Each expected number follows from the fixtures: 10 units per hour, 50 USD per unit, a 10-hour repair.
The worst case uses only past outcomes.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from copilot.core.alert_claims import Repair, open_claims
from copilot.core.impact_model import Claim, OpenOrder, OptionKind, OrderAtRisk
from copilot.core.lead_history import AlertOutcome, lead_stats
from copilot.core.recovery_options import OptionInputs, build_options, recommend
from copilot.core.spare_allocation import (
    own_supply_ready_at,
    queue_ahead,
    spare_units_free,
)
from tests.copilot.fixtures import BEARING, ECONOMICS, T0, alert, bridge, position

EARLIER = Claim("AL-1", "A-L2-01", datetime(2026, 7, 26))


def inputs(local, sisters=(), orders=(), earliest=None, **alert_args) -> OptionInputs:
    return OptionInputs(alert(**alert_args), T0, BEARING, local, sisters, bridge().transfer, None, ECONOMICS, orders,
                        2.0, earliest)


def test_queue_serves_earlier_deadlines_first_then_open_orders() -> None:
    order = OpenOrder("PO-1", "V1", 1, T0 + timedelta(days=5), T0 + timedelta(days=7))
    local = position("A", 1, (EARLIER, Claim("AL-2", "A-L1-01", datetime(2026, 7, 28, 2))), (order,))
    assert queue_ahead(local, alert()) == (EARLIER,)
    assert own_supply_ready_at(local, alert(), 1, T0) == (T0 + timedelta(days=7), "PO-1")
    assert spare_units_free(position("B", 2, (EARLIER,)), 1) == 1


def test_open_claims_close_on_repair_or_when_the_window_passes() -> None:
    first = alert("AL-1", raised=T0 - timedelta(days=2))
    stale = alert("AL-3", raised=T0 - timedelta(days=7))
    repaired = alert("AL-4", raised=T0 - timedelta(days=1))
    repairs = [Repair("A-L1-01", "spindle_bearing", T0 - timedelta(hours=1))]
    claims = open_claims([first, stale, repaired], repairs, {"spindle_bearing_wear": 6.0}, T0)
    assert [c.alert_id for c in claims] == []
    claims = open_claims([first, stale], [], {"spindle_bearing_wear": 6.0}, T0)
    assert [c.alert_id for c in claims] == ["AL-1"]


def test_lead_history_counts_only_past_failures() -> None:
    outcomes = [AlertOutcome("m", T0 - timedelta(days=10), T0 - timedelta(days=9)),
                AlertOutcome("m", T0 - timedelta(days=1), T0 + timedelta(hours=5))]
    stats = lead_stats(outcomes, "m", T0)
    assert (stats.count, stats.fastest_hours) == (1, 24.0) and lead_stats(outcomes, "other", T0).count == 0


def test_transfer_in_time_beats_waiting_for_a_late_order() -> None:
    order = OpenOrder("PO-1", "V1", 1, T0 + timedelta(days=5), T0 + timedelta(days=8))
    due = OrderAtRisk("SO-1", "Cust", "P-1", 10, date(2026, 8, 3), 100.0)
    options = build_options(inputs(position("A", 0, (), (order,)), (position("B", 1),), (due,)))
    best = recommend(options)
    assert best.kind is OptionKind.TRANSFER and best.planned and best.total_cost_usd == 650.0
    waiting = next(o for o in options if o.kind is OptionKind.OPEN_ORDER)
    # Failure assumed at the deadline (07-28 02:00); the order lands 08-02 02:00: 120 h wait + 10 h repair.
    assert waiting.downtime_hours == 130.0 and waiting.lost_contribution_usd == 130 * 10 * 50
    assert waiting.orders_at_risk == (due,)


def test_planned_repair_without_a_slot_still_costs_the_repair_hours() -> None:
    best = recommend(build_options(inputs(position("A", 1), planned_slot=False)))
    assert best.kind is OptionKind.OWN_STOCK and best.lost_production_hours == 10.0 and best.extra_cost_usd == 0


def test_emergency_premium_and_worst_case_downtime() -> None:
    options = build_options(inputs(position("A", 0), earliest=T0 + timedelta(hours=24)))
    emergency = next(o for o in options if o.kind is OptionKind.EMERGENCY_BUY)
    assert emergency.extra_cost_usd == 2000.0
    # Earliest failure 24 h after the alert, spare after 72 h: 48 h wait + 10 h repair.
    assert emergency.worst_case_downtime_hours == 58.0


def test_no_spare_needed_gives_a_single_option() -> None:
    no_spare = OptionInputs(alert(), T0, None, None, (), bridge().transfer, None, ECONOMICS, (), 2.0, None)
    options = build_options(no_spare)
    assert [o.kind for o in options] == [OptionKind.NO_SPARE_NEEDED]
