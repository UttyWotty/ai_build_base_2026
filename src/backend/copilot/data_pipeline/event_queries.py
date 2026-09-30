"""Reads the rows behind the plant event feed from the world store, for one time window.

Failures, spare movements with the stock left after each, and spare orders come from the plant and bridge tables.
Only rows that start inside the window are read; restorations are paired with their failure in the core rules.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from copilot.core.plant_events import FailureRow, MovementRow, OrderRow
from copilot.data_pipeline.world_store import WorldStore


def _ts(value: object) -> datetime:
    return pd.Timestamp(value).to_pydatetime()


def failures_between(connection_manager: WorldStore, start: datetime, end: datetime) -> list[FailureRow]:
    frame = connection_manager.execute(
        "SELECT f.asset_id, a.site_id, f.failure_mode, f.failed_at, f.restored_at FROM plant_failure_event f "
        "JOIN plant_asset a USING (asset_id) WHERE f.restored_at >= ? AND f.failed_at <= ?", [start, end])
    return [FailureRow(r.asset_id, r.site_id, r.failure_mode, _ts(r.failed_at), _ts(r.restored_at)) for r in frame.itertuples()]


def movements_between(connection_manager: WorldStore, start: datetime, end: datetime) -> list[MovementRow]:
    frame = connection_manager.execute(
        "SELECT * FROM (SELECT m.site_id, s.label, m.moved_at, m.kind, m.quantity, m.reference, "
        "sum(m.quantity) OVER (PARTITION BY m.site_id, m.spare_part_id ORDER BY m.moved_at, "
        "CASE m.kind WHEN 'emergency_receipt' THEN 0 ELSE 1 END ROWS UNBOUNDED PRECEDING) AS on_hand_after "
        "FROM bridge_spare_stock_movement m JOIN bridge_spare_part s USING (spare_part_id)) "
        "WHERE moved_at BETWEEN ? AND ?", [start, end])
    return [MovementRow(r.site_id, r.label, _ts(r.moved_at), r.kind, int(r.quantity), str(r.reference),
                        int(r.on_hand_after)) for r in frame.itertuples()]


def orders_between(connection_manager: WorldStore, start: datetime, end: datetime) -> list[OrderRow]:
    frame = connection_manager.execute(
        "SELECT o.po_id, o.site_id, s.label, coalesce(v.supplier_name, o.supplier_id) AS supplier_name, o.quantity, "
        "o.ordered_at, o.promised_at FROM bridge_spare_purchase_order o JOIN bridge_spare_part s USING (spare_part_id) "
        "LEFT JOIN supply_supplier v ON v.supplier_id = o.supplier_id WHERE o.ordered_at BETWEEN ? AND ?", [start, end])
    return [OrderRow(r.po_id, r.site_id, r.label, r.supplier_name, int(r.quantity), _ts(r.ordered_at), _ts(r.promised_at))
            for r in frame.itertuples()]
