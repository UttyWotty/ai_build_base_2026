"""Field inputs that Gemini reads: a technician's inspection photo, and a supplier's message about a delivery.

This module holds the JSON schemas the model must follow, the instructions it gets, and strict validation of what comes
back, so a malformed reply is rejected rather than trusted. A supplier's latest word on an order revises it from the
moment the message was received: a new date replaces the expected arrival, on time restores the promise, cancelled
drops the order.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time

from copilot.core.errors import CopilotError
from copilot.core.impact_model import OpenOrder

CONDITIONS = ("healthy", "early_wear", "severe_wear", "failed", "unclear")
CHANGES = ("delay", "earlier", "on_time", "cancelled", "no_delivery_change")
ON_TIME, CANCELLED = "on_time", "cancelled"
MIN_CONFIDENCE, MAX_CONFIDENCE = 0.0, 1.0
# A supplier's date is taken as delivered at midday, the middle of a receiving day.
DELIVERY_TIME = time(12, 0)

INSPECTION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "condition": {"type": "string", "enum": list(CONDITIONS)},
        "matches_predicted_failure": {"type": "boolean"},
        "confidence": {"type": "number"},
        "observations": {"type": "array", "items": {"type": "string"}},
        "advice": {"type": "string"},
    },
    "required": ["condition", "matches_predicted_failure", "confidence", "observations", "advice"],
}

SUPPLIER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"},
        "order_reference": {"type": "string"},
        "change": {"type": "string", "enum": list(CHANGES)},
        "new_delivery_date": {"type": "string", "description": "ISO date, or empty when no new date is given"},
        "reason": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["supplier_name", "order_reference", "change", "new_delivery_date", "reason", "confidence"],
}


class FieldInputError(CopilotError):
    """A model reply did not follow the schema."""


@dataclass(frozen=True)
class InspectionFinding:
    alert_id: str
    asset_id: str
    received_at: datetime
    condition: str
    matches_predicted_failure: bool
    confidence: float
    observations: tuple[str, ...]
    advice: str


@dataclass(frozen=True)
class SupplierUpdate:
    received_at: datetime
    supplier_name: str
    order_reference: str
    change: str
    new_delivery_at: datetime | None
    reason: str
    confidence: float


def inspection_instruction(asset_id: str, failure_label: str, component: str, symptoms: str, action: str) -> str:
    return (f"You are a maintenance reliability engineer. A failure-prediction model expects '{failure_label}' on the "
            f"{component.replace('_', ' ')} of asset {asset_id}, based on {symptoms}. The planned repair is: {action} "
            "Look only at the photo. Say what condition the part is in, whether what you see is consistent with the "
            "predicted failure, list concrete visual observations, and give one sentence of advice for the technician. "
            "Use 'unclear' when the photo does not show the part well enough. Confidence is between 0 and 1.")


SUPPLIER_INSTRUCTION = (
    "You read messages from suppliers to a manufacturer's purchasing team. Extract the supplier, the order reference "
    "exactly as written (for example SPO-US1-0061), whether the delivery changed, the new delivery date in ISO format "
    "(empty if none is stated), and the reason. If the message does not change a delivery, use 'no_delivery_change'. "
    "Never invent an order reference or a date. Confidence is between 0 and 1.")


def parse_inspection(raw: dict, alert_id: str, asset_id: str, received_at: datetime) -> InspectionFinding:
    condition = _choice(raw.get("condition"), CONDITIONS, "condition")
    observations = tuple(str(o).strip() for o in raw.get("observations") or [] if str(o).strip())
    return InspectionFinding(alert_id, asset_id, received_at, condition, bool(raw.get("matches_predicted_failure")),
                             _confidence(raw.get("confidence")), observations, str(raw.get("advice", "")).strip())


def parse_supplier_update(raw: dict, received_at: datetime) -> SupplierUpdate:
    change = _choice(raw.get("change"), CHANGES, "change")
    text = str(raw.get("new_delivery_date") or "").strip()
    try:
        new_at = datetime.combine(date.fromisoformat(text[:10]), DELIVERY_TIME) if text else None
    except ValueError as error:
        raise FieldInputError(f"new_delivery_date is not an ISO date: {text!r}") from error
    return SupplierUpdate(received_at, str(raw.get("supplier_name", "")).strip(), str(raw.get("order_reference", "")).strip(),
                          change, new_at, str(raw.get("reason", "")).strip(), _confidence(raw.get("confidence")))


def revise_expected(order: OpenOrder, updates: list[SupplierUpdate], now: datetime) -> OpenOrder | None:
    """Apply the supplier's latest decisive word on this order received by now; None when the order was cancelled.

    A stated new date replaces the expected arrival, "on time" restores the promised date, and "cancelled" drops the
    order. A message with no date and no such status (for example "no change") leaves the previous word standing.
    """
    known = [u for u in updates if u.order_reference == order.po_id and u.received_at <= now
             and (u.new_delivery_at is not None or u.change in (ON_TIME, CANCELLED))]
    if not known:
        return order
    latest = max(known, key=lambda u: u.received_at)
    if latest.change == CANCELLED:
        return None
    arrival = latest.new_delivery_at if latest.new_delivery_at is not None else order.promised_at
    return replace(order, expected_at=max(arrival, now))


def _choice(value: object, allowed: tuple[str, ...], name: str) -> str:
    if value not in allowed:
        raise FieldInputError(f"{name} must be one of {', '.join(allowed)}, got {value!r}")
    return str(value)


def _confidence(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise FieldInputError(f"confidence must be a number, got {value!r}") from error
    return round(min(max(number, MIN_CONFIDENCE), MAX_CONFIDENCE), 2)
