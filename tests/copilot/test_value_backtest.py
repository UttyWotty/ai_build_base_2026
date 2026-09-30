"""Tests for the value backtest: options priced at the real outcome, the baseline choice, and the summary.

A spare in hand before the failure costs nothing beyond a slot-less repair; a later spare adds the wait.
False alerts cost only the plan's extra spend, and they reduce the net value.
"""
from __future__ import annotations

from datetime import timedelta

from copilot.core.impact_analysis import assemble_report
from copilot.core.impact_model import AssetContext, OpenOrder
from copilot.core.lead_history import LeadStats
from copilot.core.recovery_options import OptionInputs
from copilot.core.value_backtest import case_value, realised_cost, summarise
from tests.copilot.fixtures import BEARING, ECONOMICS, T0, alert, bridge, position

ASSET = AssetContext("A-L1-01", "A", "A-L1", "PA")
ORDER = OpenOrder("PO-1", "V1", 1, T0 + timedelta(days=5), T0 + timedelta(days=8))


def report(planned_slot: bool = True):
    inputs = OptionInputs(alert(planned_slot=planned_slot), T0, BEARING, position("A", 0, (), (ORDER,)),
                          (position("B", 1),), bridge().transfer, None, ECONOMICS, (), 2.0, None)
    return assemble_report(inputs, ASSET, LeadStats("m", 0, None, None))


def test_a_real_failure_prices_the_wait_for_a_late_spare() -> None:
    r = report()
    failed = T0 + timedelta(hours=30)
    case = case_value(r, failed)
    assert (case.recommended_kind, case.baseline_kind) == ("transfer", "open_order")
    # Transfer lands 48 h after the alert, 18 h after the failure: 18 h wait + 10 h repair.
    assert case.copilot.lost_hours == 28.0 and case.copilot.lost_contribution_usd == 28 * 10 * 50
    # The open order lands 8 days after the alert: 162 h wait + 10 h repair.
    assert case.baseline.lost_hours == 172.0 and case.hours_saved == 144.0
    assert case.usd_saved == round(172 * 500 - (650 + 28 * 500), 2)


def test_a_spare_in_hand_before_the_failure_costs_only_a_slotless_repair() -> None:
    r = report(planned_slot=False)
    transfer = next(o for o in r.options if o.kind.value == "transfer")
    assert realised_cost(transfer, r, T0 + timedelta(days=3)).lost_hours == 10.0
    assert realised_cost(transfer, report(), T0 + timedelta(days=3)).lost_hours == 0.0


def test_false_alerts_cost_only_extra_spend_and_reduce_the_net() -> None:
    r = report()
    real, false = case_value(r, T0 + timedelta(hours=30)), case_value(r, None)
    assert false.copilot.total_usd == 650.0 and false.baseline.total_usd == 0.0
    summary = summarise([real, false])
    assert (summary.real_failures, summary.false_alerts, summary.plans_that_differ) == (1, 1, 2)
    assert summary.usd_spent_on_false_alerts == 650.0
    assert summary.net_usd == round(real.usd_saved - 650.0, 2) and summary.top_cases[0] == real
