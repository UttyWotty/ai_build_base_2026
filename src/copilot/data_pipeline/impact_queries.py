"""Point-in-time queries over the world store for the impact analysis.

Each function answers one question as it stood at a given time: stock, open spare orders, repairs, the line's rate,
customer order lines still open, and a supplier's lateness. Values come back as plain Python types or frames.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from copilot.data_pipeline.world_store import WorldStore

CANCELLED = "cancelled"
CLOSED = "closed"
RATE_LOOKBACK_DAYS = 30
SECONDS_PER_HOUR = 3600.0


def asset_row(connection_manager: WorldStore, asset_id: str) -> dict[str, object] | None:
    frame = connection_manager.execute("SELECT asset_id, site_id, line_id, asset_class FROM plant_asset WHERE asset_id = ?",
                                       [asset_id])
    return None if frame.empty else frame.iloc[0].to_dict()


def stock_on_hand(connection_manager: WorldStore, site_id: str, spare_part_id: str, as_of: datetime) -> int:
    frame = connection_manager.execute(
        "SELECT coalesce(sum(quantity), 0) AS q FROM bridge_spare_stock_movement "
        "WHERE site_id = ? AND spare_part_id = ? AND moved_at <= ?", [site_id, spare_part_id, as_of])
    return int(frame["q"].iloc[0])


def open_spare_orders(connection_manager: WorldStore, site_id: str, spare_part_id: str, as_of: datetime) -> pd.DataFrame:
    return connection_manager.execute(
        "SELECT po_id, supplier_id, quantity, promised_at FROM bridge_spare_purchase_order "
        "WHERE site_id = ? AND spare_part_id = ? AND ordered_at <= ? AND (received_at IS NULL OR received_at > ?) "
        "ORDER BY promised_at, po_id", [site_id, spare_part_id, as_of, as_of])


def repairs_until(connection_manager: WorldStore, as_of: datetime) -> pd.DataFrame:
    return connection_manager.execute(
        "SELECT asset_id, component, failed_at FROM plant_failure_event WHERE failed_at <= ?", [as_of])


def site_assets(connection_manager: WorldStore) -> dict[str, str]:
    frame = connection_manager.execute("SELECT asset_id, site_id FROM plant_asset")
    return dict(zip(frame["asset_id"], frame["site_id"]))


def asset_lines(connection_manager: WorldStore) -> dict[str, str]:
    frame = connection_manager.execute("SELECT asset_id, line_id FROM plant_asset")
    return dict(zip(frame["asset_id"], frame["line_id"]))


def line_units_per_hour(connection_manager: WorldStore, line_id: str, as_of: datetime) -> float:
    """The running production order's rate, or the line's average over the lookback when none is running."""
    running = connection_manager.execute(
        "SELECT quantity, planned_start_at, planned_end_at FROM plant_production_order "
        "WHERE line_id = ? AND planned_start_at <= ? AND planned_end_at > ?", [line_id, as_of, as_of])
    if running.empty:
        running = connection_manager.execute(
            "SELECT quantity, planned_start_at, planned_end_at FROM plant_production_order "
            "WHERE line_id = ? AND planned_start_at >= ? AND planned_end_at <= ?",
            [line_id, as_of - timedelta(days=RATE_LOOKBACK_DAYS), as_of])
    hours = (pd.to_datetime(running["planned_end_at"]) - pd.to_datetime(running["planned_start_at"])).dt.total_seconds().sum()
    return float(running["quantity"].sum() / (hours / SECONDS_PER_HOUR)) if hours else 0.0


def open_customer_lines(connection_manager: WorldStore, plant_id: str, part_ids: tuple[str, ...], as_of: date,
                        horizon_days: int) -> pd.DataFrame:
    """Customer lines booked by as_of, not yet delivered complete, committed within the horizon."""
    if not part_ids:
        return pd.DataFrame(columns=["so_line_id", "customer_name", "part_id", "qty_ordered", "committed_date", "value_usd"])
    marks = ", ".join("?" for _ in part_ids)
    return connection_manager.execute(
        "SELECT l.so_line_id, c.customer_name, l.part_id, l.qty_ordered, l.committed_date, "
        "l.qty_ordered * p.standard_cost_usd AS value_usd FROM supply_sales_order_line l "
        "JOIN supply_sales_order o USING (so_id) JOIN supply_customer c ON c.customer_id = o.customer_id "
        "JOIN supply_part p ON p.part_id = l.part_id "
        f"WHERE l.plant_id = ? AND l.part_id IN ({marks}) AND l.order_date <= ? AND l.status <> ? "
        "AND (l.last_delivery_date IS NULL OR l.last_delivery_date > ?) AND l.committed_date BETWEEN ? AND ? "
        "ORDER BY l.committed_date, l.so_line_id",
        [plant_id, *part_ids, as_of, CANCELLED, as_of, as_of, as_of + timedelta(days=horizon_days)])


def expected_days_late(connection_manager: WorldStore, supplier_id: str, start: date, end: date) -> float:
    """Mean lateness in days (early counts as zero) of lines promised in the window, as known at its end."""
    frame = connection_manager.execute(
        "SELECT avg(greatest(datediff('day', promised_date, least(coalesce(last_receipt_date, ?), ?)), 0)) AS late "
        "FROM supply_purchase_order_line WHERE supplier_id = ? AND status <> ? AND promised_date BETWEEN ? AND ?",
        [end, end, supplier_id, CANCELLED, start, end])
    value = frame["late"].iloc[0]
    return 0.0 if pd.isna(value) else float(value)


def supplier_name(connection_manager: WorldStore, supplier_id: str) -> str:
    frame = connection_manager.execute("SELECT supplier_name FROM supply_supplier WHERE supplier_id = ?", [supplier_id])
    return supplier_id if frame.empty else str(frame["supplier_name"].iloc[0])
