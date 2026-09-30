"""Builds the bridge data: validates the bridge against both worlds, then simulates each site's spares store.

Consumption comes from the plant's failure history and supplier lateness from the supply network's delivery history,
so the spares data is joined data, not a third invented world. The same seed always gives the same tables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from copilot.core.bridge_model import BridgeCatalog
from copilot.core.bridge_validator import KnownIds, validate_bridge
from copilot.core.spares_simulation import (
    Consumption,
    MovementKind,
    SparesHistory,
    simulate_spares,
)
from copilot.core.supplier_lateness import DeliveryRecord, LatenessHistory
from copilot.data_pipeline.world_store import WorldStore
from pdm_oee.core.catalog import PlantCatalog

REQUIRED_VIEWS = ("plant_site", "plant_line", "plant_asset", "plant_failure_event", "plant_machine_state",
                  "supply_plant", "supply_supplier", "supply_part", "supply_purchase_order_line")
CLOSED_STATUS = "closed"


@dataclass(frozen=True)
class BridgeData:
    """The generated tables and the manifest that describes them."""

    tables: dict[str, pd.DataFrame]
    manifest: dict[str, object]


class BridgeBuilder:
    """Validates the bridge and generates the spares history."""

    def __init__(self, bridge: BridgeCatalog, plant_catalog: PlantCatalog, connection_manager: WorldStore) -> None:
        self.bridge = bridge
        self.plant_catalog = plant_catalog
        self.connection_manager = connection_manager
        connection_manager.require(REQUIRED_VIEWS)

    def known_ids(self) -> KnownIds:
        """Ids that exist in both worlds, read from their conformed data."""
        def ids(sql: str) -> frozenset[str]:
            return frozenset(self.connection_manager.execute(sql).iloc[:, 0].astype(str))
        components = {c for cls in self.plant_catalog.plant.asset_classes.values() for c in cls.components}
        return KnownIds(ids("SELECT site_id FROM plant_site"), ids("SELECT line_id FROM plant_line"), frozenset(components),
                        ids("SELECT plant_id FROM supply_plant"), ids("SELECT supplier_id FROM supply_supplier"),
                        ids("SELECT part_id FROM supply_part"))

    def build(self, seed: int) -> BridgeData:
        """Validate, simulate, and tabulate."""
        validate_bridge(self.bridge, self.known_ids())
        start, end = self._horizon()
        lateness = LatenessHistory(self._delivery_records(), np.random.default_rng(seed))
        history = simulate_spares(self.bridge, self._consumptions(), start, end, lateness)
        tables = {"spare_part": self._spare_table(), "spare_stock_movement": _frame(history.movements),
                  "spare_purchase_order": _frame(history.purchase_orders)}
        return BridgeData(tables, _manifest(seed, start, end, history))

    def _horizon(self) -> tuple[datetime, datetime]:
        row = self.connection_manager.execute("SELECT min(start_at) AS s, max(end_at) AS e FROM plant_machine_state").iloc[0]
        return pd.Timestamp(row["s"]).to_pydatetime(), pd.Timestamp(row["e"]).to_pydatetime()

    def _consumptions(self) -> list[Consumption]:
        frame = self.connection_manager.execute(
            "SELECT a.site_id, f.component, f.failed_at, f.failure_id FROM plant_failure_event f "
            "JOIN plant_asset a USING (asset_id) ORDER BY f.failed_at, f.failure_id")
        return [Consumption(r.site_id, r.component, pd.Timestamp(r.failed_at).to_pydatetime(), str(r.failure_id))
                for r in frame.itertuples()]

    def _delivery_records(self) -> list[DeliveryRecord]:
        frame = self.connection_manager.execute(
            "SELECT supplier_id, order_date, datediff('day', promised_date, last_receipt_date) AS days_late "
            "FROM supply_purchase_order_line WHERE status = ? AND last_receipt_date IS NOT NULL", [CLOSED_STATUS])
        return [DeliveryRecord(r.supplier_id, pd.Timestamp(r.order_date).date(), int(r.days_late)) for r in frame.itertuples()]

    def _spare_table(self) -> pd.DataFrame:
        rows = []
        for spare in self.bridge.spares.values():
            row = asdict(spare)
            emergency = row.pop("emergency")
            row["emergency_lead_time_hours"] = emergency["lead_time_hours"] if emergency else None
            row["emergency_price_multiplier"] = emergency["price_multiplier"] if emergency else None
            rows.append(row)
        return pd.DataFrame(rows)


def _frame(records: tuple[object, ...]) -> pd.DataFrame:
    frame = pd.DataFrame([asdict(r) for r in records])
    if "kind" in frame:
        frame["kind"] = frame["kind"].map(lambda k: k.value)
    return frame


def _manifest(seed: int, start: datetime, end: datetime, history: SparesHistory) -> dict[str, object]:
    emergencies: dict[str, int] = {}
    for move in history.movements:
        if move.kind is MovementKind.EMERGENCY_RECEIPT:
            key = f"{move.site_id}/{move.spare_part_id}"
            emergencies[key] = emergencies.get(key, 0) + 1
    return {"seed": seed, "horizon_start": start, "horizon_end": end, "movements": len(history.movements),
            "purchase_orders": len(history.purchase_orders), "emergency_buys": dict(sorted(emergencies.items()))}
