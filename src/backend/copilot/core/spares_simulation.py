"""Simulates each site's maintenance spares store over the plant horizon: consumption, reorders, and receipts.

Repairs consume spares at their failure times; a min/max policy reorders from the spare's supplier; each order arrives
after the contracted lead time plus a lateness drawn from that supplier's real delivery history in the supply world.
A repair that finds the shelf empty is covered by an emergency buy, because the plant history shows it was repaired.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from copilot.core.bridge_model import BridgeCatalog, SparePart, StockPolicy

PO_NUMBER_WIDTH = 4


class MovementKind(str, Enum):
    """Why stock changed."""

    INITIAL = "initial"
    CONSUMPTION = "consumption"
    RECEIPT = "receipt"
    EMERGENCY_RECEIPT = "emergency_receipt"


@dataclass(frozen=True)
class Consumption:
    """A repair that needs a spare."""

    site_id: str
    component: str
    at: datetime
    reference: str


@dataclass(frozen=True)
class StockMovement:
    """One change to a site's stock of one spare; quantities are signed."""

    site_id: str
    spare_part_id: str
    moved_at: datetime
    kind: MovementKind
    quantity: int
    reference: str


@dataclass(frozen=True)
class SparePurchaseOrder:
    """A replenishment order; received_at is None when it arrives after the horizon."""

    po_id: str
    site_id: str
    spare_part_id: str
    supplier_id: str
    quantity: int
    ordered_at: datetime
    promised_at: datetime
    received_at: datetime | None


# (supplier_id, order time) -> days late (negative means early).
LatenessSampler = Callable[[str, datetime], int]


@dataclass
class _Shelf:
    """Mutable simulation state for one site and spare."""

    policy: StockPolicy
    spare: SparePart
    on_hand: int
    open_orders: list[SparePurchaseOrder] = field(default_factory=list)


@dataclass(frozen=True)
class SparesHistory:
    """Everything the simulation produced."""

    movements: tuple[StockMovement, ...]
    purchase_orders: tuple[SparePurchaseOrder, ...]


def simulate_spares(bridge: BridgeCatalog, consumptions: list[Consumption], start: datetime, end: datetime,
                    late_days: LatenessSampler) -> SparesHistory:
    """Run every site's store from start to end over the consumptions, in time order."""
    shelves = {key: _Shelf(policy, bridge.spare_by_id(policy.spare_part_id), policy.initial)
               for key, policy in sorted(bridge.policies.items())}
    movements = [StockMovement(s.policy.site_id, s.policy.spare_part_id, start, MovementKind.INITIAL, s.on_hand, "initial")
                 for s in shelves.values()]
    orders: list[SparePurchaseOrder] = []
    for event in sorted(consumptions, key=lambda c: (c.at, c.reference)):
        spare = bridge.spare_for_component(event.component)
        if spare is None or event.at > end:
            continue
        shelf = shelves[(event.site_id, spare.spare_part_id)]
        movements += _receive_due(shelf, event.at)
        movements += _consume(shelf, event)
        order = _reorder(shelf, event.at, len(orders) + 1, late_days)
        if order is not None:
            orders.append(order)
    for shelf in shelves.values():
        movements += _receive_due(shelf, end)
    finished = tuple(o if o.received_at is not None and o.received_at <= end else _still_open(o) for o in orders)
    return SparesHistory(tuple(sorted(movements, key=lambda m: (m.moved_at, m.site_id, m.spare_part_id))), finished)


def _receive_due(shelf: _Shelf, until: datetime) -> list[StockMovement]:
    due = [o for o in shelf.open_orders if o.received_at is not None and o.received_at <= until]
    shelf.open_orders = [o for o in shelf.open_orders if o not in due]
    shelf.on_hand += sum(o.quantity for o in due)
    return [StockMovement(o.site_id, o.spare_part_id, o.received_at, MovementKind.RECEIPT, o.quantity, o.po_id)
            for o in due if o.received_at is not None]


def _consume(shelf: _Shelf, event: Consumption) -> list[StockMovement]:
    needed = shelf.spare.quantity_per_repair
    moves = []
    if shelf.on_hand < needed:
        short = needed - shelf.on_hand
        moves.append(StockMovement(event.site_id, shelf.spare.spare_part_id, event.at, MovementKind.EMERGENCY_RECEIPT,
                                   short, event.reference))
        shelf.on_hand += short
    shelf.on_hand -= needed
    moves.append(StockMovement(event.site_id, shelf.spare.spare_part_id, event.at, MovementKind.CONSUMPTION, -needed,
                               event.reference))
    return moves


def _reorder(shelf: _Shelf, at: datetime, number: int, late_days: LatenessSampler) -> SparePurchaseOrder | None:
    position = shelf.on_hand + sum(o.quantity for o in shelf.open_orders)
    if position > shelf.policy.reorder_point:
        return None
    promised = at + timedelta(days=shelf.spare.contracted_lead_time_days)
    received = promised + timedelta(days=late_days(shelf.spare.supplier_id, at))
    order = SparePurchaseOrder(f"SPO-{shelf.policy.site_id}-{number:0{PO_NUMBER_WIDTH}d}", shelf.policy.site_id,
                               shelf.spare.spare_part_id, shelf.spare.supplier_id, shelf.policy.order_up_to - position,
                               at, promised, max(received, at))
    shelf.open_orders.append(order)
    return order


def _still_open(order: SparePurchaseOrder) -> SparePurchaseOrder:
    return SparePurchaseOrder(order.po_id, order.site_id, order.spare_part_id, order.supplier_id, order.quantity,
                              order.ordered_at, order.promised_at, None)
