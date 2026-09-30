"""Typed inputs and outputs of the impact analysis for one failure alert.

Inputs are point-in-time facts: what was known at the analysis time, never the alert's later outcome.
Outputs list every recovery option with its timing, cost, and customer exposure, plus the recommended one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from copilot.core.bridge_model import SparePart
from copilot.core.lead_history import LeadStats


@dataclass(frozen=True)
class AlertFacts:
    """What the alert said when it was raised."""

    alert_id: str
    asset_id: str
    failure_mode: str
    component: str
    raised_at: datetime
    # Latest time to repair before the failure is expected: half the P-F interval after the alert.
    deadline_at: datetime
    repair_hours: float
    planned_slot: bool
    priority: str


@dataclass(frozen=True)
class AssetContext:
    """Where the asset sits in both worlds."""

    asset_id: str
    site_id: str
    line_id: str
    plant_id: str


@dataclass(frozen=True)
class OpenOrder:
    """A spare order not yet received at the analysis time."""

    po_id: str
    supplier_id: str
    quantity: int
    promised_at: datetime
    # Promised time plus the supplier's expected lateness.
    expected_at: datetime


@dataclass(frozen=True)
class Claim:
    """Another open alert that needs the same spare at the same site."""

    alert_id: str
    asset_id: str
    deadline_at: datetime


@dataclass(frozen=True)
class SparePosition:
    """A site's stock of one spare at the analysis time."""

    site_id: str
    on_hand: int
    open_orders: tuple[OpenOrder, ...]
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class SupplierReliability:
    """A supplier's recent delivery record: the governed on-time metric and the expected lateness."""

    supplier_id: str
    supplier_name: str
    on_time_share: float | None
    expected_days_late: float
    window_start: date
    window_end: date
    sql_fingerprint: str


class OptionKind(str, Enum):
    """Ways to get the spare."""

    OWN_STOCK = "own_stock"
    OPEN_ORDER = "open_order"
    TRANSFER = "transfer"
    EMERGENCY_BUY = "emergency_buy"
    NEW_ORDER = "new_order"
    NO_SPARE_NEEDED = "no_spare_needed"


@dataclass(frozen=True)
class OrderAtRisk:
    """A customer order line due while the line is down."""

    so_line_id: str
    customer_name: str
    part_id: str
    quantity: int
    committed_date: date
    value_usd: float


@dataclass(frozen=True)
class RecoveryOption:
    """One way to get the spare, and what it means for the line and its customers."""

    kind: OptionKind
    source: str
    ready_at: datetime
    extra_cost_usd: float
    planned: bool
    downtime_hours: float
    lost_production_hours: float
    lost_units: float
    lost_contribution_usd: float
    orders_at_risk: tuple[OrderAtRisk, ...]
    # Downtime if the failure comes as early as the fastest past alert of this mode; None without history.
    worst_case_downtime_hours: float | None

    @property
    def total_cost_usd(self) -> float:
        """Extra spend plus lost contribution: what the option costs beyond a normal planned repair."""
        return self.extra_cost_usd + self.lost_contribution_usd


@dataclass(frozen=True)
class LineEconomics:
    """How fast the line produces and what an unproduced unit costs."""

    units_per_hour: float
    contribution_usd_per_unit: float


@dataclass(frozen=True)
class ImpactReport:
    """Everything the impact analysis found for one alert."""

    alert: AlertFacts
    asset: AssetContext
    as_of: datetime
    spare: SparePart | None
    local: SparePosition | None
    sisters: tuple[SparePosition, ...]
    supplier: SupplierReliability | None
    economics: LineEconomics
    lead: LeadStats
    options: tuple[RecoveryOption, ...]
    recommended: RecoveryOption
    assumptions: tuple[str, ...]
