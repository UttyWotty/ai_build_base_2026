"""Rules that turn an alert into a draft work order: repair deadline, planned slot, priority, and deduplication.

The deadline is half the failure mode's P-F interval after the alert (the usual P-F/2 rule), capped at the horizon.
The slot is the first planned stop that starts after the alert, is long enough for the repair, and ends by the deadline.
An alert is attached to an earlier alert on the same asset and mode that is still before its deadline, to an open
corrective order, or to a preventive task due before the deadline, instead of drafting a new order.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from pdm_oee.core.enums import WorkType

DEADLINE_SHARE_OF_PF = 0.5
HOURS_PER_DAY = 24


class Outcome(str, Enum):
    NEW_DRAFT = "new_draft"
    ATTACHED_TO_OPEN_ALERT = "attached_to_open_alert"
    ATTACHED_TO_OPEN_ORDER = "attached_to_open_order"
    ATTACHED_TO_PREVENTIVE = "attached_to_preventive"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


HIGH_CRITICALITY = "A"


@dataclass(frozen=True)
class Slot:
    """Where the repair goes: a planned stop, or an unplanned stop of the repair's length."""

    start: pd.Timestamp | None
    end: pd.Timestamp | None

    @property
    def planned(self) -> bool:
        return self.start is not None


def deadline(raised_at: pd.Timestamp, pf_interval_days: float, horizon_hours: int) -> pd.Timestamp:
    hours = min(horizon_hours, pf_interval_days * HOURS_PER_DAY * DEADLINE_SHARE_OF_PF)
    return raised_at + pd.Timedelta(hours=hours)


def planned_slot(planned_stops: pd.DataFrame, raised_at: pd.Timestamp, due: pd.Timestamp, repair_hours: float) -> Slot:
    """The first planned stop of the asset (start_at, end_at) that fits the repair before the deadline."""
    length = pd.Timedelta(hours=repair_hours)
    fits = planned_stops[(planned_stops["start_at"] >= raised_at) & (planned_stops["end_at"] - planned_stops["start_at"] >= length)
                         & (planned_stops["start_at"] + length <= due)].sort_values("start_at")
    if fits.empty:
        return Slot(None, None)
    start = fits["start_at"].iloc[0]
    return Slot(start, start + length)


def priority(criticality: str, slot: Slot) -> Priority:
    if criticality == HIGH_CRITICALITY and not slot.planned:
        return Priority.P1
    if criticality == HIGH_CRITICALITY or not slot.planned:
        return Priority.P2
    return Priority.P3


def dedup(orders: pd.DataFrame, asset_id: str, component: str, raised_at: pd.Timestamp, due: pd.Timestamp) -> tuple[Outcome, str | None]:
    """Attach to an open corrective order on the component, or a preventive task on the asset due by the deadline."""
    mine = orders[orders["asset_id"] == asset_id]
    open_corrective = mine[(mine["work_type"] == WorkType.CORRECTIVE.value) & (mine["component"] == component)
                           & (mine["created_at"] <= raised_at) & (mine["closed_at"] > raised_at)]
    if len(open_corrective):
        return Outcome.ATTACHED_TO_OPEN_ORDER, str(open_corrective["wo_id"].iloc[0])
    due_dates = pd.to_datetime(mine["due_date"])
    preventive = mine[(mine["work_type"] == WorkType.PREVENTIVE.value) & (mine["created_at"] <= raised_at)
                      & (due_dates >= raised_at.normalize()) & (due_dates <= due)]
    if len(preventive):
        return Outcome.ATTACHED_TO_PREVENTIVE, str(preventive.sort_values("due_date")["wo_id"].iloc[0])
    return Outcome.NEW_DRAFT, None


def open_alert(earlier: list[dict], asset_id: str, failure_mode: str, raised_at: pd.Timestamp) -> str | None:
    """The id of an earlier drafted alert on the same asset and mode whose deadline has not passed."""
    for alert in reversed(earlier):
        if (alert["asset_id"], alert["failure_mode"]) == (asset_id, failure_mode) and alert["deadline_at"] > raised_at \
                and alert["outcome"] == Outcome.NEW_DRAFT.value:
            return str(alert["alert_id"])
    return None
