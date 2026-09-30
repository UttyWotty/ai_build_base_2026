"""Derived attributes of sales order lines, sales orders, and shipments, as defined in semantic/ontology.yaml.

Lines get delivered quantity, completion date, first-shipment facts, and the two on-time flags (committed and requested).
Orders roll up first ship date and complete-on-first-shipment across their non-cancelled lines; shipments get the carrier on-time flag.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform.completion import completion_dates

CANCELLED = "cancelled"


def _on_or_before(dates: pd.Series, deadline: pd.Series) -> pd.Series:
    return (dates.notna() & (pd.to_datetime(dates) <= pd.to_datetime(deadline))).astype(bool)


def _nullable_dates(values: pd.Series) -> pd.Series:
    values = values.astype(object)
    return values.where(values.notna(), None)


def add_sales_line_rollups(lines: pd.DataFrame, shipment_lines: pd.DataFrame, shipment: pd.DataFrame) -> pd.DataFrame:
    """Add delivery and first-shipment rollups and the on-time flags."""
    events = shipment_lines.merge(shipment[["shipment_id", "ship_date", "delivered_date"]], on="shipment_id", how="left")
    delivered = events[events["delivered_date"].notna()]
    ordered = lines.set_index("so_line_id")["qty_ordered"]
    completed = completion_dates(delivered, "so_line_id", "delivered_date", "qty_shipped", "shipment_id", ordered)
    first = events.sort_values(["so_line_id", "ship_date", "shipment_id"], kind="mergesort").groupby("so_line_id").first()
    frame = lines.copy()
    frame["qty_delivered"] = frame["so_line_id"].map(delivered.groupby("so_line_id")["qty_shipped"].sum()).fillna(0).astype(int)
    frame["last_delivery_date"] = _nullable_dates(frame["so_line_id"].map(completed))
    frame["first_ship_date"] = _nullable_dates(frame["so_line_id"].map(first["ship_date"]))
    frame["qty_on_first_shipment"] = frame["so_line_id"].map(first["qty_shipped"]).fillna(0).astype(int)
    frame["is_complete_on_first_shipment"] = (frame["qty_on_first_shipment"] == frame["qty_ordered"]).astype(bool)
    frame["is_delivered_complete_by_committed"] = _on_or_before(frame["last_delivery_date"], frame["committed_date"])
    frame["is_delivered_complete_by_requested"] = _on_or_before(frame["last_delivery_date"], frame["requested_date"])
    return frame


def add_sales_order_rollups(orders: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Add first_ship_date and is_complete_on_first_shipment (over non-cancelled lines; False when all are cancelled)."""
    live = lines[lines["status"] != CANCELLED]
    first_ship = lines.dropna(subset=["first_ship_date"]).groupby("so_id")["first_ship_date"].min()
    complete = live.groupby("so_id")["is_complete_on_first_shipment"].all()
    frame = orders.copy()
    frame["first_ship_date"] = _nullable_dates(frame["so_id"].map(first_ship))
    frame["is_complete_on_first_shipment"] = frame["so_id"].map(complete).eq(True)
    return frame


def add_shipment_flags(shipment: pd.DataFrame) -> pd.DataFrame:
    """Add is_delivered_by_planned."""
    frame = shipment.copy()
    frame["is_delivered_by_planned"] = _on_or_before(frame["delivered_date"], frame["planned_delivery_date"])
    return frame
