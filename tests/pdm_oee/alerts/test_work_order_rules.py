"""Hand-built checks of the draft work order rules: deadline, planned slot, priority, and deduplication.

Times are on one Monday-to-Saturday stretch; the planned stop is the weekend from Saturday 06:00.
Each rule is exercised on both sides of its boundary.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from pdm_oee.core.work_order_rules import (
    Outcome,
    Priority,
    Slot,
    deadline,
    dedup,
    open_alert,
    planned_slot,
    priority,
)

RAISED = pd.Timestamp("2026-06-11 08:00")
WEEKEND = pd.DataFrame({"start_at": [pd.Timestamp("2026-06-11 12:00"), pd.Timestamp("2026-06-13 06:00")],
                        "end_at": [pd.Timestamp("2026-06-11 12:30"), pd.Timestamp("2026-06-15 06:00")]})


def test_deadline_is_half_the_pf_interval_capped_at_the_horizon() -> None:
    assert deadline(RAISED, 6, 168) == RAISED + pd.Timedelta(hours=72)
    assert deadline(RAISED, 21, 168) == RAISED + pd.Timedelta(hours=168)


def test_slot_is_the_first_planned_stop_long_enough_before_the_deadline() -> None:
    slot = planned_slot(WEEKEND, RAISED, RAISED + pd.Timedelta(hours=72), repair_hours=10)
    assert (slot.start, slot.end) == (pd.Timestamp("2026-06-13 06:00"), pd.Timestamp("2026-06-13 16:00"))
    assert not planned_slot(WEEKEND, RAISED, RAISED + pd.Timedelta(hours=24), repair_hours=10).planned


def test_priority_matrix() -> None:
    planned, unplanned = Slot(RAISED, RAISED), Slot(None, None)
    assert [priority("A", unplanned), priority("A", planned), priority("B", unplanned), priority("B", planned)] == \
        [Priority.P1, Priority.P2, Priority.P2, Priority.P3]


def test_dedup_prefers_open_orders_then_due_preventive_tasks() -> None:
    orders = pd.DataFrame({
        "wo_id": ["1", "2", "3"], "asset_id": "A", "work_type": ["corrective", "preventive", "preventive"],
        "component": ["spindle_bearing", None, None],
        "created_at": pd.to_datetime(["2026-06-11 07:00", "2026-06-01 00:00", "2026-06-01 00:00"]),
        "closed_at": pd.to_datetime(["2026-06-11 09:00", "2026-06-13 00:00", "2026-06-30 00:00"]),
        "due_date": [None, date(2026, 6, 12), date(2026, 6, 30)]})
    due = RAISED + pd.Timedelta(hours=72)
    assert dedup(orders, "A", "spindle_bearing", RAISED, due) == (Outcome.ATTACHED_TO_OPEN_ORDER, "1")
    assert dedup(orders, "A", "coolant_pump", RAISED, due) == (Outcome.ATTACHED_TO_PREVENTIVE, "2")
    assert dedup(orders, "B", "coolant_pump", RAISED, due) == (Outcome.NEW_DRAFT, None)


def test_open_alert_until_its_deadline() -> None:
    earlier = [{"alert_id": "X", "asset_id": "A", "failure_mode": "m", "deadline_at": RAISED + pd.Timedelta(hours=10),
                "outcome": Outcome.NEW_DRAFT.value}]
    assert open_alert(earlier, "A", "m", RAISED + pd.Timedelta(hours=5)) == "X"
    assert open_alert(earlier, "A", "m", RAISED + pd.Timedelta(hours=11)) is None
    assert open_alert(earlier, "A", "other", RAISED) is None
