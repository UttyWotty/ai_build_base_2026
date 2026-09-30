"""Answers "what does this alert mean for parts, the line, and customers?" as it stood at a point in time.

It gathers point-in-time facts from the world store and the governed supply metrics, then hands them to the pure
impact rules. The analysis time defaults to the moment the alert was raised.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import pandas as pd

from copilot.core.alert_claims import Repair, open_claims
from copilot.core.bridge_model import BridgeCatalog, SparePart
from copilot.core.decisions import Decision, apply_decisions
from copilot.core.errors import ImpactError
from copilot.core.field_inputs import SupplierUpdate, revise_expected
from copilot.core.impact_analysis import assemble_report
from copilot.core.impact_model import (
    AlertFacts,
    AssetContext,
    ImpactReport,
    LineEconomics,
    OpenOrder,
    OrderAtRisk,
    SparePosition,
    SupplierReliability,
)
from copilot.core.lead_history import lead_stats
from copilot.core.recovery_options import OptionInputs
from copilot.data_pipeline import impact_queries as q
from copilot.data_pipeline.world_store import WorldStore
from copilot.services.alert_book import AlertBook
from copilot.services.supplier_reliability import SupplierReliabilityService
from pdm_oee.core.catalog import PlantCatalog

CUSTOMER_HORIZON_DAYS = 60
REQUIRED_VIEWS = ("plant_asset", "plant_failure_event", "plant_production_order", "bridge_spare_stock_movement",
                  "bridge_spare_purchase_order", "supply_sales_order_line", "supply_sales_order", "supply_customer",
                  "supply_part", "supply_purchase_order_line", "supply_supplier")


class ImpactService:
    """Impact analysis for alerts."""

    def __init__(self, bridge: BridgeCatalog, plant_catalog: PlantCatalog, alerts: AlertBook,
                 reliability: SupplierReliabilityService, connection_manager: WorldStore,
                 decisions: Callable[[], list[Decision]] | None = None,
                 supplier_updates: Callable[[], list[SupplierUpdate]] | None = None) -> None:
        self.bridge = bridge
        # Supplier messages read by Gemini revise open orders from the moment they arrived.
        self.supplier_updates = supplier_updates
        # Approved decisions change stock and queues from their moment on; None means no approvals are applied.
        self.decisions = decisions
        self.alerts = alerts
        self.reliability = reliability
        self.connection_manager = connection_manager
        connection_manager.require(REQUIRED_VIEWS)
        self.pf_days = {mode_id: mode.pf_interval_days for cls in plant_catalog.plant.asset_classes.values()
                        for mode_id, mode in cls.failure_modes.items() if mode.pf_interval_days is not None}
        self.asset_sites = q.site_assets(connection_manager)
        self.asset_lines = q.asset_lines(connection_manager)

    def open_alerts(self, as_of: datetime) -> list[AlertFacts]:
        """Alerts that opened a draft and were still waiting for their repair at as_of, earliest deadline first."""
        claims = open_claims(self.alerts.drafting, self._repairs(as_of), self.pf_days, as_of)
        return [self.alerts.get(c.alert_id) for c in claims]

    def _repairs(self, as_of: datetime) -> list[Repair]:
        return [Repair(r.asset_id, r.component, pd.Timestamp(r.failed_at).to_pydatetime())
                for r in q.repairs_until(self.connection_manager, as_of).itertuples()]

    def analyse(self, alert_id: str, as_of: datetime | None = None) -> ImpactReport:
        """The impact report for an alert at as_of (default: when it was raised)."""
        alert = self.alerts.get(alert_id)
        now = as_of or alert.raised_at
        if now < alert.raised_at:
            raise ImpactError(f"{alert_id} was raised at {alert.raised_at}, after the requested time {now}")
        asset = self._asset(alert.asset_id)
        spare = self.bridge.spare_for_component(alert.component)
        supplier = self.reliability.assess(spare.supplier_id, now) if spare else None
        local, sisters = (self._positions(alert, asset.site_id, spare, supplier, now) if spare else (None, ()))
        link = self.bridge.lines[asset.line_id]
        lead = lead_stats(self.alerts.outcomes, alert.failure_mode, now)
        earliest = None if lead.fastest_hours is None else alert.raised_at + timedelta(hours=lead.fastest_hours)
        inputs = OptionInputs(
            alert=alert, as_of=now, spare=spare, local=local, sisters=sisters, transfer=self.bridge.transfer,
            supplier=supplier,
            economics=LineEconomics(q.line_units_per_hour(self.connection_manager, asset.line_id, now),
                                    link.contribution_usd_per_unit),
            candidate_orders=self._candidate_orders(asset, link.part_ids, now),
            dispatch_buffer_days=self.bridge.dispatch_buffer_days, earliest_failure_at=earliest)
        return assemble_report(inputs, asset, lead)

    def _asset(self, asset_id: str) -> AssetContext:
        row = q.asset_row(self.connection_manager, asset_id)
        if row is None:
            raise ImpactError(f"Unknown asset {asset_id}")
        site = str(row["site_id"])
        return AssetContext(asset_id, site, str(row["line_id"]), self.bridge.sites[site].plant_id)

    def _positions(self, alert: AlertFacts, site_id: str, spare: SparePart, supplier: SupplierReliability | None,
                   now: datetime) -> tuple[SparePosition, tuple[SparePosition, ...]]:
        repairs = self._repairs(now)

        def position(site: str) -> SparePosition:
            candidates = [a for a in self.alerts.drafting if self.asset_sites.get(a.asset_id) == site
                          and a.component == spare.component]
            if site == site_id and alert not in candidates:
                candidates.append(alert)
            raw = SparePosition(site, q.stock_on_hand(self.connection_manager, site, spare.spare_part_id, now),
                                self._open_orders(site, spare, supplier, now),
                                open_claims(candidates, repairs, self.pf_days, now))
            if self.decisions is None:
                return raw
            return apply_decisions(raw, spare.spare_part_id, self.decisions(), now, for_alert=alert.alert_id)
        return position(site_id), tuple(position(s) for s in self.bridge.sister_sites(site_id))

    def _open_orders(self, site: str, spare: SparePart, supplier: SupplierReliability | None,
                     now: datetime) -> tuple[OpenOrder, ...]:
        late = timedelta(days=supplier.expected_days_late if supplier else 0.0)
        frame = q.open_spare_orders(self.connection_manager, site, spare.spare_part_id, now)
        orders = [OpenOrder(r.po_id, r.supplier_id, int(r.quantity), pd.Timestamp(r.promised_at).to_pydatetime(),
                            max(pd.Timestamp(r.promised_at).to_pydatetime() + late, now)) for r in frame.itertuples()]
        updates = self.supplier_updates() if self.supplier_updates else []
        return tuple(revise_expected(o, updates, now) for o in orders)

    def _candidate_orders(self, asset: AssetContext, part_ids: tuple[str, ...], now: datetime) -> tuple[OrderAtRisk, ...]:
        frame = q.open_customer_lines(self.connection_manager, asset.plant_id, part_ids, now.date(), CUSTOMER_HORIZON_DAYS)
        return tuple(OrderAtRisk(r.so_line_id, r.customer_name, r.part_id, int(r.qty_ordered),
                                 pd.Timestamp(r.committed_date).date(), round(float(r.value_usd), 2))
                     for r in frame.itertuples())
