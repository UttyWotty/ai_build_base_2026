"""Typed model of the governed bridge between the plant and the supply network.

It holds the site-to-plant links, the maintenance spares with their suppliers and stock policies, the urgent
transfer terms, each line's customer parts and contribution, and the customer-risk rule.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SiteLink:
    """A plant site and the supply-network plant its customer orders ship from."""

    site_id: str
    plant_id: str
    label: str


@dataclass(frozen=True)
class EmergencySource:
    """A faster, dearer source for a spare: a broker or the manufacturer's express service."""

    lead_time_hours: float
    price_multiplier: float


@dataclass(frozen=True)
class SparePart:
    """The spare a repair of one plant component consumes."""

    component: str
    spare_part_id: str
    label: str
    unit_cost_usd: float
    quantity_per_repair: int
    supplier_id: str
    contracted_lead_time_days: int
    emergency: EmergencySource | None


@dataclass(frozen=True)
class StockPolicy:
    """Min/max policy for one spare at one site."""

    site_id: str
    spare_part_id: str
    initial: int
    reorder_point: int
    order_up_to: int


@dataclass(frozen=True)
class TransferTerms:
    """Urgent spare transfer between sites."""

    lead_time_hours: float
    cost_usd: float


@dataclass(frozen=True)
class LineLink:
    """What a line makes for customers and what an unproduced unit costs in lost contribution."""

    line_id: str
    part_ids: tuple[str, ...]
    contribution_usd_per_unit: float


@dataclass(frozen=True)
class BridgeCatalog:
    """The whole bridge definition."""

    sites: dict[str, SiteLink]
    spares: dict[str, SparePart]
    policies: dict[tuple[str, str], StockPolicy]
    transfer: TransferTerms
    lines: dict[str, LineLink]
    dispatch_buffer_days: float

    def spare_for_component(self, component: str) -> SparePart | None:
        """The spare a component's repair consumes, or None when it needs none."""
        return self.spares.get(component)

    def spare_by_id(self, spare_part_id: str) -> SparePart:
        """The spare with this id."""
        return next(s for s in self.spares.values() if s.spare_part_id == spare_part_id)

    def sister_sites(self, site_id: str) -> tuple[str, ...]:
        """Every other site, in id order."""
        return tuple(sorted(s for s in self.sites if s != site_id))
