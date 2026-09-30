"""Draws how late a supplier delivers, from that supplier's own recent history in the supply world.

The pool for an order is the supplier's closed purchase order lines ordered in the trailing window before it.
Draws come from a seeded generator, so the same history and seed always give the same spare deliveries.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np

TRAILING_WINDOW_DAYS = 90


@dataclass(frozen=True)
class DeliveryRecord:
    """One closed supply-world purchase order line: when it was ordered and how late it arrived."""

    supplier_id: str
    order_date: date
    days_late: int


class LatenessHistory:
    """Samples days late for a supplier and an order time."""

    def __init__(self, records: list[DeliveryRecord], rng: np.random.Generator,
                 window_days: int = TRAILING_WINDOW_DAYS) -> None:
        self.by_supplier: dict[str, list[DeliveryRecord]] = defaultdict(list)
        for record in sorted(records, key=lambda r: (r.supplier_id, r.order_date, r.days_late)):
            self.by_supplier[record.supplier_id].append(record)
        self.rng = rng
        self.window = timedelta(days=window_days)

    def pool(self, supplier_id: str, at: datetime) -> list[int]:
        """Days late of the supplier's lines ordered in the window before the order time."""
        day = at.date()
        return [r.days_late for r in self.by_supplier.get(supplier_id, [])
                if day - self.window <= r.order_date < day]

    def __call__(self, supplier_id: str, at: datetime) -> int:
        """One draw; an empty pool means the supplier has no recent history, so it is taken as on time."""
        pool = self.pool(supplier_id, at)
        if not pool:
            return 0
        return int(pool[int(self.rng.integers(len(pool)))])
