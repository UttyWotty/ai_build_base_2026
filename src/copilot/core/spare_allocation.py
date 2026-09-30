"""Decides when a spare can be ready for an alert, given stock, open orders, and other alerts ahead in the queue.

Open alerts for the same spare at a site are served earliest deadline first; ties go to the lower alert id.
Stock serves first, then open orders in expected arrival order, so an alert's unit is the next one after the queue ahead.
"""
from __future__ import annotations

from datetime import datetime

from copilot.core.impact_model import AlertFacts, Claim, SparePosition


def queue_ahead(position: SparePosition, alert: AlertFacts) -> tuple[Claim, ...]:
    """Claims that are served before this alert."""
    key = (alert.deadline_at, alert.alert_id)
    return tuple(c for c in position.claims if c.alert_id != alert.alert_id and (c.deadline_at, c.alert_id) < key)


def own_supply_ready_at(position: SparePosition, alert: AlertFacts, quantity: int, as_of: datetime) -> tuple[datetime, str] | None:
    """When this site's own stock or open orders can cover the alert, and from which source; None if they cannot."""
    needed_before = len(queue_ahead(position, alert)) * quantity
    supply: list[tuple[datetime, str]] = [(as_of, "stock")] * position.on_hand
    for order in sorted(position.open_orders, key=lambda o: (o.expected_at, o.po_id)):
        supply += [(order.expected_at, order.po_id)] * order.quantity
    if len(supply) < needed_before + quantity:
        return None
    return supply[needed_before + quantity - 1]


def spare_units_free(position: SparePosition, quantity: int) -> int:
    """Stock on hand that the site's own open alerts do not need: what it could lend today."""
    return max(position.on_hand - len(position.claims) * quantity, 0)
