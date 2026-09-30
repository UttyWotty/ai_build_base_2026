"""Weekly inventory simulation for one plant-part combination: receive, ship, snapshot, reorder.

Stock is consumed first-in-first-out by planned ship day, so shortages produce partial shipments and backorders.
A min-max policy places purchase orders whose arrival dates come from supplier behaviour, which makes fill rate and OTD emergent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import count

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic.config import StoryConfig
from supply_ontology.data_pipeline.synthetic.supplier_behavior import (
    on_time_share,
    sample_arrival_offset,
    sample_confirmations,
)
from supply_ontology.data_pipeline.synthetic.timeline import (
    DAYS_PER_WEEK,
    LAST_DAY_OFFSET,
)

ORDER_WEEKDAY = 4
CANCELLED_PO_SHARE = 0.01
SPLIT_RECEIPT_SHARE = 0.05
SPLIT_FIRST_SHARE = (0.5, 0.9)
SPLIT_GAP_DAYS = (7, 14)


@dataclass(frozen=True)
class ComboPlan:
    """Replenishment parameters for one plant-part combination."""

    plant_id: str
    part_id: str
    supplier_id: str
    lead_days: int
    moq: int
    base_on_time_share: float
    degrading: bool
    reorder_point: float
    order_up_to: float


@dataclass
class SimRecords:
    """Row buffers filled by the simulation; converted to frames once all combos have run."""

    allocations: list[tuple[str, int, int]] = field(default_factory=list)
    po_lines: list[tuple[int, str, str, str, int, int, int, bool]] = field(default_factory=list)
    confirmations: list[tuple[int, int, int, int, int]] = field(default_factory=list)
    receipts: list[tuple[int, int, int]] = field(default_factory=list)
    snapshots: list[tuple[str, str, int, int]] = field(default_factory=list)


@dataclass
class _ComboState:
    on_hand: int
    pending: list[tuple[int, int, int]] = field(default_factory=list)
    backlog: list[list] = field(default_factory=list)


def simulate_combo(
    plan: ComboPlan, lines: pd.DataFrame, weeks: int, stories: StoryConfig,
    rng: np.random.Generator, records: SimRecords, po_sequence: count,
) -> None:
    """Run the weekly loop for one combination, appending rows to `records`.

    `lines` holds the combination's non-cancelled sales lines with so_line_id, planned_ship_day, qty_ordered.
    """
    state = _ComboState(on_hand=int(math.ceil(plan.order_up_to)))
    ordered = lines.sort_values(["planned_ship_day", "so_line_id"], kind="mergesort")
    due_week = np.clip(ordered["planned_ship_day"].to_numpy() // DAYS_PER_WEEK, 0, None)
    rows = list(zip(ordered["so_line_id"], ordered["planned_ship_day"], ordered["qty_ordered"], due_week))
    cursor = 0
    for week in range(weeks):
        lots = _receive(state, week, records)
        while cursor < len(rows) and rows[cursor][3] <= week:
            so_line_id, planned_day, qty, _ = rows[cursor]
            state.backlog.append([so_line_id, int(planned_day), int(qty)])
            cursor += 1
        _ship(state, lots, week, records)
        week_end = week * DAYS_PER_WEEK + LAST_DAY_OFFSET
        records.snapshots.append((plan.plant_id, plan.part_id, week_end, state.on_hand))
        _maybe_reorder(plan, state, week, stories, rng, records, po_sequence)


def _receive(state: _ComboState, week: int, records: SimRecords) -> list[list[int]]:
    """Book this week's arrivals; return stock lots as [available_day, qty], opening stock first."""
    week_start, week_end = week * DAYS_PER_WEEK, week * DAYS_PER_WEEK + LAST_DAY_OFFSET
    lots = [[week_start, state.on_hand]]
    remaining = []
    for arrival_day, qty, po_seq in sorted(state.pending):
        if arrival_day <= week_end:
            records.receipts.append((po_seq, arrival_day, qty))
            lots.append([max(arrival_day, week_start), qty])
            state.on_hand += qty
        else:
            remaining.append((arrival_day, qty, po_seq))
    state.pending = remaining
    return lots


def _ship(state: _ComboState, lots: list[list[int]], week: int, records: SimRecords) -> None:
    """Ship backlog lines FIFO from the stock lots; a line ships no earlier than its planned day."""
    week_start = week * DAYS_PER_WEEK
    still_open = []
    for entry in state.backlog:
        so_line_id, planned_day, remaining = entry
        shipped, latest_lot_day = 0, 0
        for lot in lots:
            if shipped == remaining:
                break
            take = min(lot[1], remaining - shipped)
            if take > 0:
                lot[1] -= take
                shipped += take
                latest_lot_day = max(latest_lot_day, lot[0])
        if shipped:
            ship_day = max(planned_day, week_start, latest_lot_day)
            records.allocations.append((so_line_id, ship_day, shipped))
            state.on_hand -= shipped
        if shipped < remaining:
            still_open.append([so_line_id, planned_day, remaining - shipped])
    state.backlog = still_open


def _maybe_reorder(
    plan: ComboPlan, state: _ComboState, week: int, stories: StoryConfig,
    rng: np.random.Generator, records: SimRecords, po_sequence: count,
) -> None:
    position = state.on_hand + sum(q for _, q, _ in state.pending) - sum(e[2] for e in state.backlog)
    if position > plan.reorder_point:
        return
    qty = max(int(math.ceil(plan.order_up_to - position)), plan.moq)
    order_day = week * DAYS_PER_WEEK + ORDER_WEEKDAY
    po_seq = next(po_sequence)
    if rng.random() < CANCELLED_PO_SHARE:
        records.po_lines.append((po_seq, plan.plant_id, plan.part_id, plan.supplier_id, qty, order_day, order_day + plan.lead_days, True))
        return
    confirmations = sample_confirmations(order_day, plan.lead_days, rng)
    for confirmation in confirmations:
        records.confirmations.append(
            (po_seq, confirmation.confirmed_day, confirmation.confirmed_at_day, confirmation.confirmed_hour, len(records.confirmations))
        )
    promised_day = confirmations[-1].confirmed_day
    share = on_time_share(plan.base_on_time_share, plan.degrading, promised_day, stories)
    # Receiving for this week has already run, so the earliest possible arrival is next Monday.
    next_week_start = (week + 1) * DAYS_PER_WEEK
    arrival = max(next_week_start, promised_day + sample_arrival_offset(share, rng))
    records.po_lines.append((po_seq, plan.plant_id, plan.part_id, plan.supplier_id, qty, order_day, promised_day, False))
    state.pending.extend(_split_arrivals(qty, arrival, po_seq, rng))


def _split_arrivals(qty: int, arrival: int, po_seq: int, rng: np.random.Generator) -> list[tuple[int, int, int]]:
    if qty < 2 or rng.random() >= SPLIT_RECEIPT_SHARE:
        return [(arrival, qty, po_seq)]
    first = max(1, int(qty * rng.uniform(*SPLIT_FIRST_SHARE)))
    gap = int(rng.integers(SPLIT_GAP_DAYS[0], SPLIT_GAP_DAYS[1] + 1))
    return [(arrival, first, po_seq), (arrival + gap, qty - first, po_seq)]
