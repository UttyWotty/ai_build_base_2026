"""Tests for the spares store simulation and the supplier lateness sampler.

Repairs consume stock, the min/max policy reorders, orders arrive late by the sampled days, and an empty shelf is
covered by an emergency buy. The sampler draws only from the supplier's window before the order.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from copilot.core.spares_simulation import Consumption, MovementKind, simulate_spares
from copilot.core.supplier_lateness import DeliveryRecord, LatenessHistory
from tests.copilot.fixtures import bridge

START, END = datetime(2026, 1, 1), datetime(2026, 12, 31)


def stock(history, site: str, until: datetime) -> int:
    return sum(m.quantity for m in history.movements if m.site_id == site and m.moved_at <= until)


def test_consumption_reorders_and_late_receipt() -> None:
    events = [Consumption("A", "spindle_bearing", datetime(2026, 2, 1), "F1")]
    history = simulate_spares(bridge(), events, START, END, lambda supplier, at: 3)
    order = history.purchase_orders[0]
    assert (order.site_id, order.quantity, order.supplier_id) == ("A", 1, "V1")
    assert order.promised_at == datetime(2026, 2, 15) and order.received_at == datetime(2026, 2, 18)
    assert stock(history, "A", datetime(2026, 2, 17)) == 1 and stock(history, "A", datetime(2026, 2, 18)) == 2


def test_empty_shelf_is_covered_by_an_emergency_buy() -> None:
    events = [Consumption("A", "spindle_bearing", datetime(2026, 3, 1, h), f"F{h}") for h in (1, 2, 3)]
    history = simulate_spares(bridge(), events, START, END, lambda supplier, at: 0)
    kinds = [m.kind for m in history.movements if m.site_id == "A"]
    assert kinds.count(MovementKind.EMERGENCY_RECEIPT) == 1
    assert min(stock(history, "A", m.moved_at) for m in history.movements if m.site_id == "A") >= 0


def test_components_without_a_spare_and_events_after_the_horizon_are_ignored() -> None:
    events = [Consumption("A", "tool_changer", datetime(2026, 2, 1), "F1"),
              Consumption("A", "spindle_bearing", datetime(2027, 2, 1), "F2")]
    history = simulate_spares(bridge(), events, START, END, lambda supplier, at: 0)
    assert history.purchase_orders == () and all(m.kind is MovementKind.INITIAL for m in history.movements)


def test_orders_arriving_after_the_horizon_stay_open() -> None:
    events = [Consumption("A", "spindle_bearing", END - timedelta(days=2), "F1")]
    history = simulate_spares(bridge(), events, START, END, lambda supplier, at: 0)
    assert history.purchase_orders[0].received_at is None


def test_lateness_draws_only_from_the_suppliers_trailing_window() -> None:
    records = [DeliveryRecord("V1", date(2026, 1, 10), 9), DeliveryRecord("V1", date(2025, 6, 1), -50),
               DeliveryRecord("V2", date(2026, 1, 10), 100)]
    sampler = LatenessHistory(records, np.random.default_rng(0))
    assert sampler.pool("V1", datetime(2026, 2, 1)) == [9]
    assert sampler("V1", datetime(2026, 2, 1)) == 9 and sampler("V3", datetime(2026, 2, 1)) == 0
