"""Conforms ERP sales order headers and items into the sales_order and sales_order_line entities.

Line ids join the sales document and the item number; the ERP's confirmed delivery date is the canonical committed date.
Statuses are decoded from ERP codes.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.dates import as_dates
from supply_ontology.data_pipeline.conform.keys import SO_ITEM_WIDTH, composite_id
from supply_ontology.data_pipeline.conform.source_layout import Sources
from supply_ontology.data_pipeline.conform.status_codes import decode_status


def conform_sales_order(sources: Sources) -> pd.DataFrame:
    erp = sources[layout.ERP_SO_HEADERS]
    return pd.DataFrame({
        "so_id": erp["SALES_DOC"].astype(str),
        "customer_id": erp["SOLD_TO"].astype(str),
        "order_date": as_dates(erp["DOC_DATE"]),
        "status": decode_status(erp["STATUS"], "sales order"),
    })


def conform_sales_order_line(sources: Sources) -> pd.DataFrame:
    erp = sources[layout.ERP_SO_ITEMS]
    return pd.DataFrame({
        "so_line_id": composite_id(erp["SALES_DOC"], erp["ITEM"], SO_ITEM_WIDTH),
        "so_id": erp["SALES_DOC"].astype(str),
        "part_id": erp["MATERIAL"].astype(str),
        "plant_id": erp["PLANT"].astype(str),
        "qty_ordered": erp["ORDER_QTY"].astype(int),
        "order_date": as_dates(erp["CREATED_ON"]),
        "requested_date": as_dates(erp["REQ_DELIV_DATE"]),
        "committed_date": as_dates(erp["CONFIRMED_DELIV_DATE"]),
        "status": decode_status(erp["STATUS"], "sales order line"),
    })
