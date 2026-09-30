"""Derived attributes of purchase order lines and receipts, as defined in semantic/ontology.yaml.

PO lines get received quantity, completion date, and the on-time-by-promised flag.
Receipts get goods value at receipt-date FX, freight allocated by goods value share, duty for cross-border receipts, and landed cost.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform.completion import completion_dates
from supply_ontology.data_pipeline.conform.keys import map_or_fail
from supply_ontology.data_pipeline.conform.reference import usd_rates_on

NO_DUTY = 0.0


def add_po_line_rollups(po_lines: pd.DataFrame, receipts: pd.DataFrame) -> pd.DataFrame:
    """Add qty_received, last_receipt_date, and is_received_complete_by_promised."""
    ordered = po_lines.set_index("po_line_id")["qty_ordered"]
    received = receipts.groupby("po_line_id")["qty_received"].sum()
    completed = completion_dates(receipts, "po_line_id", "receipt_date", "qty_received", "receipt_id", ordered)
    frame = po_lines.copy()
    frame["qty_received"] = frame["po_line_id"].map(received).fillna(0).astype(int)
    frame["last_receipt_date"] = frame["po_line_id"].map(completed).astype(object)
    frame["last_receipt_date"] = frame["last_receipt_date"].where(frame["last_receipt_date"].notna(), None)
    on_time = frame["last_receipt_date"].notna() & (
        pd.to_datetime(frame["last_receipt_date"]) <= pd.to_datetime(frame["promised_date"])
    )
    frame["is_received_complete_by_promised"] = on_time.astype(bool)
    return frame


def add_receipt_costs(
    receipts: pd.DataFrame, po_lines: pd.DataFrame, part: pd.DataFrame, supplier: pd.DataFrame,
    plant: pd.DataFrame, shipment: pd.DataFrame, fx_rate: pd.DataFrame, duty_rate: pd.DataFrame,
) -> pd.DataFrame:
    """Add goods_value_usd, freight_allocated_usd, duty_usd, and landed_cost_usd."""
    line = po_lines.set_index("po_line_id").loc[receipts["po_line_id"]].reset_index(drop=True)
    frame = receipts.reset_index(drop=True).copy()
    rates = usd_rates_on(fx_rate, line["currency"], frame["receipt_date"])
    frame["goods_value_usd"] = frame["qty_received"] * line["unit_price_local"].to_numpy() * rates.to_numpy()
    freight = map_or_fail(frame["inbound_shipment_id"], shipment.set_index("shipment_id")["freight_cost_usd"], "receipt shipment freight")
    shipment_goods = frame.groupby("inbound_shipment_id")["goods_value_usd"].transform("sum")
    frame["freight_allocated_usd"] = (freight * frame["goods_value_usd"] / shipment_goods).where(shipment_goods > 0, 0.0)
    supplier_country = line["supplier_id"].map(supplier.set_index("supplier_id")["country"])
    plant_country = line["plant_id"].map(plant.set_index("plant_id")["country"])
    category = line["part_id"].map(part.set_index("part_id")["category"])
    duty_lookup = duty_rate.set_index(["origin_country", "category"])["duty_pct"]
    duty_pct = map_or_fail(pd.Series(list(zip(supplier_country, category))), duty_lookup, "duty rate for (origin, category)")
    cross_border = (supplier_country != plant_country).to_numpy()
    frame["duty_usd"] = (frame["goods_value_usd"] * duty_pct.to_numpy()).where(cross_border, NO_DUTY)
    frame["landed_cost_usd"] = frame["goods_value_usd"] + frame["freight_allocated_usd"] + frame["duty_usd"]
    return frame
