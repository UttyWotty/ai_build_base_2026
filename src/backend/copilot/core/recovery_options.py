"""Builds every way to get the spare for an alert and prices each one: extra spend, downtime, lost output, orders at risk.

Downtime rule: a spare ready by the repair deadline allows a planned repair, which costs production only when no planned
slot is available. Otherwise the failure is assumed at the deadline (or now, if later) and the line waits for the spare.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from copilot.core.bridge_model import SparePart, TransferTerms
from copilot.core.impact_model import (
    AlertFacts,
    LineEconomics,
    OptionKind,
    OrderAtRisk,
    RecoveryOption,
    SparePosition,
    SupplierReliability,
)
from copilot.core.spare_allocation import own_supply_ready_at, spare_units_free

SECONDS_PER_HOUR = 3600.0
OWN_STOCK_SOURCE = "stock"
# Tie-break order when two options cost the same and are ready at the same time.
KIND_PREFERENCE = (OptionKind.NO_SPARE_NEEDED, OptionKind.OWN_STOCK, OptionKind.OPEN_ORDER, OptionKind.TRANSFER,
                   OptionKind.NEW_ORDER, OptionKind.EMERGENCY_BUY)


@dataclass(frozen=True)
class OptionInputs:
    """Everything needed to build and price the options for one alert."""

    alert: AlertFacts
    as_of: datetime
    spare: SparePart | None
    local: SparePosition | None
    sisters: tuple[SparePosition, ...]
    transfer: TransferTerms
    supplier: SupplierReliability | None
    economics: LineEconomics
    candidate_orders: tuple[OrderAtRisk, ...]
    dispatch_buffer_days: float
    # Raised time plus the fastest past lead time of this failure mode; None without history.
    earliest_failure_at: datetime | None


@dataclass(frozen=True)
class _Sourcing:
    kind: OptionKind
    source: str
    ready_at: datetime
    extra_cost_usd: float


def build_options(inputs: OptionInputs) -> tuple[RecoveryOption, ...]:
    """Every feasible option, priced, cheapest first."""
    options = [_price(s, inputs) for s in _sourcings(inputs)]
    return tuple(sorted(options, key=_rank))


def recommend(options: tuple[RecoveryOption, ...]) -> RecoveryOption:
    """The lowest total cost; ties go to the earliest ready time, then the simplest kind."""
    return min(options, key=_rank)


def _rank(option: RecoveryOption) -> tuple[float, datetime, int]:
    return round(option.total_cost_usd, 2), option.ready_at, KIND_PREFERENCE.index(option.kind)


def _sourcings(inputs: OptionInputs) -> list[_Sourcing]:
    spare, now = inputs.spare, inputs.as_of
    if spare is None:
        return [_Sourcing(OptionKind.NO_SPARE_NEEDED, "none", now, 0.0)]
    found = []
    if inputs.local is not None:
        own = own_supply_ready_at(inputs.local, inputs.alert, spare.quantity_per_repair, now)
        if own is not None:
            kind = OptionKind.OWN_STOCK if own[1] == OWN_STOCK_SOURCE else OptionKind.OPEN_ORDER
            found.append(_Sourcing(kind, own[1], own[0], 0.0))
    found += [_Sourcing(OptionKind.TRANSFER, sister.site_id, now + timedelta(hours=inputs.transfer.lead_time_hours),
                        inputs.transfer.cost_usd)
              for sister in inputs.sisters if spare_units_free(sister, spare.quantity_per_repair) >= spare.quantity_per_repair]
    if spare.emergency is not None:
        premium = spare.unit_cost_usd * (spare.emergency.price_multiplier - 1) * spare.quantity_per_repair
        found.append(_Sourcing(OptionKind.EMERGENCY_BUY, "broker", now + timedelta(hours=spare.emergency.lead_time_hours),
                               premium))
    late_days = inputs.supplier.expected_days_late if inputs.supplier is not None else 0.0
    found.append(_Sourcing(OptionKind.NEW_ORDER, spare.supplier_id,
                           now + timedelta(days=spare.contracted_lead_time_days + late_days), 0.0))
    return found


def _price(sourcing: _Sourcing, inputs: OptionInputs) -> RecoveryOption:
    alert = inputs.alert
    failure_at = max(alert.deadline_at, inputs.as_of)
    planned = sourcing.ready_at <= alert.deadline_at and alert.deadline_at >= inputs.as_of
    if planned:
        start, end = sourcing.ready_at, sourcing.ready_at + timedelta(hours=alert.repair_hours)
        lost_hours = 0.0 if alert.planned_slot else alert.repair_hours
    else:
        start = failure_at
        end = max(sourcing.ready_at, failure_at) + timedelta(hours=alert.repair_hours)
        lost_hours = _hours(end - start)
    lost_units = lost_hours * inputs.economics.units_per_hour
    at_risk = _orders_in_window(inputs.candidate_orders, start, end, inputs.dispatch_buffer_days) if lost_hours else ()
    return RecoveryOption(sourcing.kind, sourcing.source, sourcing.ready_at, round(sourcing.extra_cost_usd, 2), planned,
                          round(_hours(end - start), 1), round(lost_hours, 1), round(lost_units, 1),
                          round(lost_units * inputs.economics.contribution_usd_per_unit, 2), at_risk,
                          _worst_case_hours(sourcing.ready_at, inputs))


def _worst_case_hours(ready_at: datetime, inputs: OptionInputs) -> float | None:
    """Downtime if the failure comes at the earliest plausible time: the wait for the spare plus the repair."""
    if inputs.earliest_failure_at is None:
        return None
    failure_at = max(inputs.earliest_failure_at, inputs.as_of)
    wait = max(ready_at - failure_at, timedelta(0))
    return round(_hours(wait) + inputs.alert.repair_hours, 1)


def _orders_in_window(orders: tuple[OrderAtRisk, ...], start: datetime, end: datetime,
                      buffer_days: float) -> tuple[OrderAtRisk, ...]:
    last = (end + timedelta(days=buffer_days)).date()
    return tuple(o for o in orders if start.date() <= o.committed_date <= last)


def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / SECONDS_PER_HOUR
