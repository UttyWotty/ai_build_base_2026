"""Production orders: each line runs one product at a time, changing product at a shift boundary every few shifts.

Every shift of a line therefore has exactly one product, and the first shift of each new order starts with a changeover.
Planned quantities are sized from the CNC ideal cycle so orders look like real ERP orders.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.synthetic.reference import ORDER_SHIFTS, SHIFT_HOURS

PLANNING_EFFICIENCY = 0.85
BOTTLENECK_CLASS = "cnc_machining_centre"
SECONDS_PER_HOUR = 3600


@dataclass(frozen=True)
class OrderPlan:
    """Orders per line and the product each line runs in each shift."""

    orders: pd.DataFrame
    line_shifts: pd.DataFrame


def plan_orders(lines: pd.DataFrame, products: pd.DataFrame, routings: pd.DataFrame,
                shifts: pd.DataFrame, rng: np.random.Generator) -> OrderPlan:
    """Split every line's shifts into orders of a few shifts each, alternating products."""
    orders, line_shifts = [], []
    for line in lines.itertuples():
        site_shifts = shifts[shifts["site_id"] == line.site_id].reset_index(drop=True)
        choices = products.loc[products["family"] == line.family, "product_id"].tolist()
        position, previous, number = 0, None, 0
        while position < len(site_shifts):
            length = int(rng.integers(ORDER_SHIFTS[0], ORDER_SHIFTS[1] + 1))
            block = site_shifts.iloc[position:position + length]
            product = str(rng.choice([p for p in choices if p != previous]))
            number += 1
            order_id = f"PO-{line.line_id}-{number:04d}"
            orders.append(_order(order_id, line.line_id, product, block, routings))
            line_shifts += [{"line_id": line.line_id, "shift_id": s.shift_id, "product_id": product, "order_id": order_id,
                             "changeover": previous is not None and i == 0} for i, s in enumerate(block.itertuples())]
            position, previous = position + length, product
    return OrderPlan(pd.DataFrame(orders), pd.DataFrame(line_shifts))


def _order(order_id: str, line_id: str, product: str, block: pd.DataFrame, routings: pd.DataFrame) -> dict:
    cycle = routings[(routings["product_id"] == product) & (routings["asset_class"] == BOTTLENECK_CLASS)]["ideal_cycle_s"].iloc[0]
    quantity = int(len(block) * SHIFT_HOURS * SECONDS_PER_HOUR * PLANNING_EFFICIENCY / cycle)
    return {"order_id": order_id, "line_id": line_id, "product_id": product, "quantity": quantity,
            "planned_start_minute": int(block["start_minute"].iloc[0]), "planned_end_minute": int(block["end_minute"].iloc[-1])}
