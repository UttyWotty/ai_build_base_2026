"""The plant event feed: alerts, breakdowns, restorations, and spare movements, merged into one timeline.

Events are built from plain rows, so the rules (titles, severities, what counts as an event) are testable without data.
Only events at or before the end of the window are ever included, so the feed never shows the future.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

SECONDS_PER_HOUR = 3600.0
MAX_EVENTS = 200


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    GOOD = "good"


@dataclass(frozen=True)
class PlantEvent:
    """One thing that happened, as the feed shows it."""

    at: datetime
    kind: str
    site_id: str
    subject: str
    title: str
    severity: Severity
    alert_id: str | None = None


@dataclass(frozen=True)
class FailureRow:
    asset_id: str
    site_id: str
    failure_mode: str
    failed_at: datetime
    restored_at: datetime


@dataclass(frozen=True)
class MovementRow:
    site_id: str
    spare_label: str
    moved_at: datetime
    kind: str
    quantity: int
    reference: str
    on_hand_after: int


@dataclass(frozen=True)
class OrderRow:
    po_id: str
    site_id: str
    spare_label: str
    supplier_name: str
    quantity: int
    ordered_at: datetime
    promised_at: datetime


@dataclass(frozen=True)
class AlertRow:
    alert_id: str
    asset_id: str
    site_id: str
    failure_mode: str
    priority: str
    raised_at: datetime
    # False when the alert was attached to an existing work order instead of opening its own draft.
    opens_draft: bool = True


def _mode(text: str) -> str:
    return text.replace("_", " ")


def failure_events(row: FailureRow) -> list[PlantEvent]:
    down = (row.restored_at - row.failed_at).total_seconds() / SECONDS_PER_HOUR
    return [PlantEvent(row.failed_at, "breakdown", row.site_id, row.asset_id,
                       f"{row.asset_id} stopped: {_mode(row.failure_mode)}", Severity.CRITICAL),
            PlantEvent(row.restored_at, "restored", row.site_id, row.asset_id,
                       f"{row.asset_id} back in production after {down:.1f} h", Severity.GOOD)]


def movement_event(row: MovementRow) -> PlantEvent | None:
    if row.kind == "consumption":
        return PlantEvent(row.moved_at, "spare_used", row.site_id, row.spare_label,
                          f"{row.spare_label} used at {row.site_id}, {row.on_hand_after} left",
                          Severity.WARNING if row.on_hand_after == 0 else Severity.INFO)
    if row.kind == "receipt":
        return PlantEvent(row.moved_at, "spare_received", row.site_id, row.spare_label,
                          f"{row.quantity} x {row.spare_label} received at {row.site_id} ({row.reference})", Severity.GOOD)
    if row.kind == "emergency_receipt":
        return PlantEvent(row.moved_at, "emergency_buy", row.site_id, row.spare_label,
                          f"Emergency buy of {row.spare_label} at {row.site_id}: the shelf was empty", Severity.CRITICAL)
    return None


def order_event(row: OrderRow) -> PlantEvent:
    return PlantEvent(row.ordered_at, "spare_ordered", row.site_id, row.spare_label,
                      f"{row.site_id} ordered {row.quantity} x {row.spare_label} from {row.supplier_name}, "
                      f"promised {row.promised_at:%d %b}", Severity.INFO)


def alert_event(row: AlertRow) -> PlantEvent:
    if not row.opens_draft:
        return PlantEvent(row.raised_at, "alert_covered", row.site_id, row.asset_id,
                          f"Alert on {row.asset_id} ({_mode(row.failure_mode)}) is already covered by an open work order",
                          Severity.INFO, alert_id=row.alert_id)
    return PlantEvent(row.raised_at, "alert", row.site_id, row.asset_id,
                      f"{row.priority} alert: {_mode(row.failure_mode)} predicted on {row.asset_id}", Severity.WARNING,
                      alert_id=row.alert_id)


def build_feed(alerts: list[AlertRow], failures: list[FailureRow], movements: list[MovementRow],
               orders: list[OrderRow], start: datetime, end: datetime) -> list[PlantEvent]:
    """Every event in [start, end], newest first, capped at MAX_EVENTS."""
    events = [alert_event(a) for a in alerts] + [e for f in failures for e in failure_events(f)]
    events += [e for m in movements if (e := movement_event(m)) is not None] + [order_event(o) for o in orders]
    window = [e for e in events if start <= e.at <= end]
    return sorted(window, key=lambda e: (e.at, e.kind), reverse=True)[:MAX_EVENTS]
