"""Renders canonical truth tables as ERP exports: xlsx master data and Parquet transactions with ERP column names.

The ERP splits composite ids into document number and item, encodes statuses as single-letter codes, and knows shipments only by bill of lading.
Promised dates are absent here because suppliers confirm them in the portal, which the conform step must resolve.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from supply_ontology.data_pipeline.synthetic.world_tables import (
    STATUS_CANCELLED,
    STATUS_CLOSED,
    STATUS_OPEN,
    WorldExtras,
)

ERP_STATUS_CODE = {STATUS_OPEN: "A", STATUS_CLOSED: "C", STATUS_CANCELLED: "X"}
ID_SEPARATOR = "-"


def render_erp(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> list[SourceFile]:
    """Return every ERP source file."""
    return [*_masters(tables, extras), *_procurement(tables, extras), *_sales(tables), _inventory(tables)]


def _split_item(ids: pd.Series) -> tuple[pd.Series, pd.Series]:
    parts = ids.str.rsplit(ID_SEPARATOR, n=1)
    return parts.str[0], parts.str[1].astype(int)


def _masters(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> list[SourceFile]:
    supplier, part, customer = tables["supplier"], tables["part"], tables["customer"]
    vendors = pd.DataFrame({
        "VENDOR_NO": supplier["supplier_id"], "NAME": supplier["supplier_name"], "COUNTRY_KEY": supplier["country"],
        "REGION": supplier["region"], "TIER": supplier["tier"], "CURRENCY": supplier["currency"],
    })
    items = pd.DataFrame({
        "MATERIAL": part["part_id"], "DESCRIPTION": part["description"], "CATEGORY": part["category"],
        "FAMILY": part["family"], "BASE_UOM": part["uom"], "STD_COST_USD": part["standard_cost_usd"],
        "CASE_PACK": part["part_id"].map(extras.part_case_packs.set_index("part_id")["case_pack"]),
    })
    plants = tables["plant"].rename(columns={"plant_id": "PLANT", "plant_name": "NAME", "country": "COUNTRY", "region": "REGION"})
    customers = pd.DataFrame({
        "SOLD_TO": customer["customer_id"], "NAME": customer["customer_name"], "SEGMENT": customer["segment"],
        "COUNTRY": customer["country"], "REGION": customer["region"],
    })
    info_records = tables["supplier_part"].rename(columns={
        "supplier_id": "VENDOR_NO", "part_id": "MATERIAL", "unit_price_local": "NET_PRICE",
        "moq": "MIN_ORDER_QTY", "contracted_lead_time_days": "PLANNED_DELIV_DAYS",
    })
    return [
        SourceFile("erp/vendor_master.xlsx", vendors, FileFormat.XLSX),
        SourceFile("erp/item_master.xlsx", items, FileFormat.XLSX),
        SourceFile("erp/plants.xlsx", plants, FileFormat.XLSX),
        SourceFile("erp/customer_master.xlsx", customers, FileFormat.XLSX),
        SourceFile("erp/purchasing_info_records.xlsx", info_records, FileFormat.XLSX),
    ]


def _procurement(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> list[SourceFile]:
    po = tables["purchase_order_line"]
    po_number, po_item = _split_item(po["po_line_id"])
    lines = pd.DataFrame({
        "PO_NUMBER": po_number, "PO_ITEM": po_item, "VENDOR_NO": po["supplier_id"], "MATERIAL": po["part_id"],
        "PLANT": po["plant_id"], "ORDER_QTY": po["qty_ordered"], "NET_PRICE": po["unit_price_local"],
        "CURRENCY": po["currency"], "PO_DATE": po["order_date"], "STATUS": po["status"].map(ERP_STATUS_CODE),
    })
    receipt = tables["receipt"]
    receipt_po, receipt_item = _split_item(receipt["po_line_id"])
    bol_of = extras.shipment_details.set_index("shipment_id")["bol_number"]
    receipts = pd.DataFrame({
        "MAT_DOC": receipt["receipt_id"], "PO_NUMBER": receipt_po, "PO_ITEM": receipt_item,
        "QTY": receipt["qty_received"], "POSTING_DATE": receipt["receipt_date"],
        "BILL_OF_LADING": receipt["inbound_shipment_id"].map(bol_of),
    })
    return [
        SourceFile("erp/purchase_order_lines.parquet", lines, FileFormat.PARQUET),
        SourceFile("erp/goods_receipts.parquet", receipts, FileFormat.PARQUET),
    ]


def _sales(tables: dict[str, pd.DataFrame]) -> list[SourceFile]:
    header, line = tables["sales_order"], tables["sales_order_line"]
    headers = pd.DataFrame({
        "SALES_DOC": header["so_id"], "SOLD_TO": header["customer_id"], "DOC_DATE": header["order_date"],
        "STATUS": header["status"].map(ERP_STATUS_CODE),
    })
    sales_doc, item = _split_item(line["so_line_id"])
    items = pd.DataFrame({
        "SALES_DOC": sales_doc, "ITEM": item, "MATERIAL": line["part_id"], "PLANT": line["plant_id"],
        "ORDER_QTY": line["qty_ordered"], "CREATED_ON": line["order_date"], "REQ_DELIV_DATE": line["requested_date"],
        "CONFIRMED_DELIV_DATE": line["committed_date"], "STATUS": line["status"].map(ERP_STATUS_CODE),
    })
    return [
        SourceFile("erp/sales_order_headers.parquet", headers, FileFormat.PARQUET),
        SourceFile("erp/sales_order_items.parquet", items, FileFormat.PARQUET),
    ]


def _inventory(tables: dict[str, pd.DataFrame]) -> SourceFile:
    snapshot = tables["inventory_snapshot"]
    frame = pd.DataFrame({
        "PLANT": snapshot["plant_id"], "MATERIAL": snapshot["part_id"], "WEEK_ENDING": snapshot["snapshot_date"],
        "UNRESTRICTED_QTY": snapshot["qty_on_hand"],
    })
    return SourceFile("erp/inventory_weekly.parquet", frame, FileFormat.PARQUET)
