"""The expected layout of the source-system exports: relative file paths and the columns conform relies on.

These constants describe the external systems as the conform step sees them; they deliberately do not import the generator.
check_sources verifies that every expected file and column is present before any transformation runs.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from supply_ontology.data_pipeline.conform.errors import ConformError

ERP_VENDORS = "erp/vendor_master.xlsx"
ERP_ITEMS = "erp/item_master.xlsx"
ERP_PLANTS = "erp/plants.xlsx"
ERP_CUSTOMERS = "erp/customer_master.xlsx"
ERP_INFO_RECORDS = "erp/purchasing_info_records.xlsx"
ERP_PO_LINES = "erp/purchase_order_lines.parquet"
ERP_RECEIPTS = "erp/goods_receipts.parquet"
ERP_SO_HEADERS = "erp/sales_order_headers.parquet"
ERP_SO_ITEMS = "erp/sales_order_items.parquet"
ERP_INVENTORY = "erp/inventory_weekly.parquet"
TMS_SHIPMENTS = "tms/shipments.parquet"
TMS_OUTBOUND_LINES = "tms/outbound_lines.parquet"
PORTAL_CONFIRMATIONS = "supplier_portal/confirmations.xlsx"
TREASURY_FX = "treasury/fx_rates.xlsx"
TRADE_DUTY = "trade/duty_rates.xlsx"
MDM_CROSSWALK = "mdm/partner_crosswalk.xlsx"

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    ERP_VENDORS: ("VENDOR_NO", "NAME", "COUNTRY_KEY", "REGION", "TIER", "CURRENCY"),
    ERP_ITEMS: ("MATERIAL", "DESCRIPTION", "CATEGORY", "FAMILY", "BASE_UOM", "STD_COST_USD", "CASE_PACK"),
    ERP_PLANTS: ("PLANT", "NAME", "COUNTRY", "REGION"),
    ERP_CUSTOMERS: ("SOLD_TO", "NAME", "SEGMENT", "COUNTRY", "REGION"),
    ERP_INFO_RECORDS: ("VENDOR_NO", "MATERIAL", "NET_PRICE", "MIN_ORDER_QTY", "PLANNED_DELIV_DAYS"),
    ERP_PO_LINES: ("PO_NUMBER", "PO_ITEM", "VENDOR_NO", "MATERIAL", "PLANT", "ORDER_QTY", "NET_PRICE", "CURRENCY", "PO_DATE", "STATUS"),
    ERP_RECEIPTS: ("MAT_DOC", "PO_NUMBER", "PO_ITEM", "QTY", "POSTING_DATE", "BILL_OF_LADING"),
    ERP_SO_HEADERS: ("SALES_DOC", "SOLD_TO", "DOC_DATE", "STATUS"),
    ERP_SO_ITEMS: ("SALES_DOC", "ITEM", "MATERIAL", "PLANT", "ORDER_QTY", "CREATED_ON", "REQ_DELIV_DATE", "CONFIRMED_DELIV_DATE", "STATUS"),
    ERP_INVENTORY: ("PLANT", "MATERIAL", "WEEK_ENDING", "UNRESTRICTED_QTY"),
    TMS_SHIPMENTS: ("TMS_REF", "DIRECTION", "CARRIER_SCAC", "ORIGIN_PARTNER", "DEST_PARTNER", "PICKUP_TS_UTC",
                    "PLANNED_DELIVERY_TS_UTC", "DELIVERED_TS_UTC", "FREIGHT_AMOUNT", "FREIGHT_CCY", "BOL_NUMBER"),
    TMS_OUTBOUND_LINES: ("TMS_REF", "ORDER_REF", "ITEM_CODE", "QTY", "UOM"),
    PORTAL_CONFIRMATIONS: ("PO Number", "Line", "Supplier", "Confirmed Delivery", "Confirmed At"),
    TREASURY_FX: ("Date", "Currency", "Rate per USD"),
    TRADE_DUTY: ("Origin", "Category", "Duty %"),
    MDM_CROSSWALK: ("PARTNER_CODE", "PARTNER_TYPE", "ERP_NUMBER"),
}

Sources = Mapping[str, pd.DataFrame]


def check_sources(sources: Sources) -> None:
    """Fail with every missing file and column listed, or return silently when the layout is complete."""
    problems = []
    for path, columns in REQUIRED_COLUMNS.items():
        if path not in sources:
            problems.append(f"missing file {path}")
            continue
        missing = [c for c in columns if c not in sources[path].columns]
        if missing:
            problems.append(f"{path} lacks columns {missing}")
    if problems:
        raise ConformError("Source layout problems: " + "; ".join(problems))
