"""Runs every conform step in dependency order and returns one frame per ontology entity.

Base entities come first, then FX-dependent shipments, then derived attributes that need several entities.
The result is checked against the ontology: each frame must carry exactly the entity's attributes, in declared order.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.core.ontology_model import Ontology
from supply_ontology.data_pipeline.conform import (
    derived_inventory,
    derived_procurement,
    derived_sales,
)
from supply_ontology.data_pipeline.conform.errors import ConformError
from supply_ontology.data_pipeline.conform.logistics import (
    conform_outbound_shipment_line,
    conform_shipment,
)
from supply_ontology.data_pipeline.conform.masters import (
    conform_customer,
    conform_part,
    conform_plant,
    conform_supplier,
    conform_supplier_part,
    party_countries,
)
from supply_ontology.data_pipeline.conform.procurement import (
    conform_purchase_order_line,
    conform_receipt,
)
from supply_ontology.data_pipeline.conform.reference import (
    conform_duty_rate,
    conform_fx_rate,
    conform_inventory_snapshot,
)
from supply_ontology.data_pipeline.conform.sales import (
    conform_sales_order,
    conform_sales_order_line,
)
from supply_ontology.data_pipeline.conform.source_layout import Sources, check_sources


def conform_sources(sources: Sources, ontology: Ontology, trailing_window_days: int) -> dict[str, pd.DataFrame]:
    """Conform all sources into entity frames that match the ontology exactly."""
    check_sources(sources)
    t: dict[str, pd.DataFrame] = {
        "supplier": conform_supplier(sources), "part": conform_part(sources), "plant": conform_plant(sources),
        "customer": conform_customer(sources), "supplier_part": conform_supplier_part(sources),
        "fx_rate": conform_fx_rate(sources), "duty_rate": conform_duty_rate(sources),
        "sales_order": conform_sales_order(sources), "sales_order_line": conform_sales_order_line(sources),
        "purchase_order_line": conform_purchase_order_line(sources), "receipt": conform_receipt(sources),
        "outbound_shipment_line": conform_outbound_shipment_line(sources),
        "inventory_snapshot": conform_inventory_snapshot(sources),
    }
    countries = party_countries(t["supplier"], t["plant"], t["customer"])
    t["shipment"] = derived_sales.add_shipment_flags(conform_shipment(sources, countries, t["fx_rate"]))
    t["purchase_order_line"] = derived_procurement.add_po_line_rollups(t["purchase_order_line"], t["receipt"])
    t["receipt"] = derived_procurement.add_receipt_costs(
        t["receipt"], t["purchase_order_line"], t["part"], t["supplier"], t["plant"],
        t["shipment"], t["fx_rate"], t["duty_rate"],
    )
    t["sales_order_line"] = derived_sales.add_sales_line_rollups(t["sales_order_line"], t["outbound_shipment_line"], t["shipment"])
    t["sales_order"] = derived_sales.add_sales_order_rollups(t["sales_order"], t["sales_order_line"])
    t["inventory_snapshot"] = derived_inventory.add_inventory_values(
        t["inventory_snapshot"], t["part"], t["outbound_shipment_line"], t["shipment"],
        t["sales_order_line"], trailing_window_days,
    )
    return order_like_ontology(t, ontology)


def order_like_ontology(tables: dict[str, pd.DataFrame], ontology: Ontology) -> dict[str, pd.DataFrame]:
    """Reorder columns and rows to the ontology; fail on any missing or extra entity or attribute."""
    if set(tables) != set(ontology.entities):
        raise ConformError(f"Entity mismatch: missing {sorted(set(ontology.entities) - set(tables))}, extra {sorted(set(tables) - set(ontology.entities))}")
    ordered = {}
    for name, entity in ontology.entities.items():
        columns = list(entity.attributes)
        frame = tables[name]
        if set(frame.columns) != set(columns):
            raise ConformError(f"{name}: missing {sorted(set(columns) - set(frame.columns))}, extra {sorted(set(frame.columns) - set(columns))}")
        ordered[name] = frame[columns].sort_values(list(entity.key), kind="mergesort").reset_index(drop=True)
    return ordered
