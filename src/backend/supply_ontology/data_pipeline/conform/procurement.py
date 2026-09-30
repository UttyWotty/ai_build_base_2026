"""Conforms purchase order lines and goods receipts, resolving promised dates from the supplier portal.

The promised date is the latest confirmation by confirmation time; lines never confirmed fall back to order date plus contract lead time.
Receipts are linked to inbound shipments through the bill of lading, the only identifier the ERP and TMS share.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.dates import as_dates, day_first_dates
from supply_ontology.data_pipeline.conform.keys import (
    PO_ITEM_WIDTH,
    composite_id,
    map_or_fail,
)
from supply_ontology.data_pipeline.conform.source_layout import Sources
from supply_ontology.data_pipeline.conform.status_codes import decode_status


def latest_confirmations(sources: Sources) -> pd.Series:
    """Promised date per po_line_id from the most recent portal confirmation."""
    portal = sources[layout.PORTAL_CONFIRMATIONS]
    frame = pd.DataFrame({
        "po_line_id": composite_id(portal["PO Number"], portal["Line"], PO_ITEM_WIDTH),
        "confirmed_at": pd.to_datetime(portal["Confirmed At"], utc=True),
        "promised_date": day_first_dates(portal["Confirmed Delivery"]),
    })
    latest = frame.sort_values(["po_line_id", "confirmed_at"], kind="mergesort").groupby("po_line_id").last()
    return latest["promised_date"]


def conform_purchase_order_line(sources: Sources) -> pd.DataFrame:
    erp = sources[layout.ERP_PO_LINES]
    frame = pd.DataFrame({
        "po_line_id": composite_id(erp["PO_NUMBER"], erp["PO_ITEM"], PO_ITEM_WIDTH),
        "po_id": erp["PO_NUMBER"].astype(str),
        "supplier_id": erp["VENDOR_NO"].astype(str),
        "part_id": erp["MATERIAL"].astype(str),
        "plant_id": erp["PLANT"].astype(str),
        "qty_ordered": erp["ORDER_QTY"].astype(int),
        "unit_price_local": erp["NET_PRICE"].astype(float),
        "currency": erp["CURRENCY"],
        "order_date": as_dates(erp["PO_DATE"]),
    })
    info = sources[layout.ERP_INFO_RECORDS].set_index(["VENDOR_NO", "MATERIAL"])["PLANNED_DELIV_DAYS"]
    lead_days = map_or_fail(pd.Series(list(zip(frame["supplier_id"], frame["part_id"]))), info, "purchasing info record")
    fallback = pd.to_datetime(frame["order_date"]) + pd.to_timedelta(lead_days.astype(int).to_numpy(), unit="D")
    confirmed = frame["po_line_id"].map(latest_confirmations(sources))
    frame["promised_date"] = confirmed.where(confirmed.notna(), as_dates(fallback))
    frame["status"] = decode_status(erp["STATUS"], "purchase order line")
    return frame


def conform_receipt(sources: Sources) -> pd.DataFrame:
    erp = sources[layout.ERP_RECEIPTS]
    shipment_of_bol = sources[layout.TMS_SHIPMENTS].set_index("BOL_NUMBER")["TMS_REF"]
    return pd.DataFrame({
        "receipt_id": erp["MAT_DOC"].astype(str),
        "po_line_id": composite_id(erp["PO_NUMBER"], erp["PO_ITEM"], PO_ITEM_WIDTH),
        "inbound_shipment_id": map_or_fail(erp["BILL_OF_LADING"], shipment_of_bol, "receipt bill of lading"),
        "qty_received": erp["QTY"].astype(int),
        "receipt_date": as_dates(erp["POSTING_DATE"]),
    })
