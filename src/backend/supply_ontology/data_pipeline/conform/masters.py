"""Conforms ERP master data exports into the supplier, part, plant, customer, and supplier_part entities.

Masters are clean in the ERP, so conforming them is a rename into canonical attribute names plus type normalisation.
The functions also expose a party-country lookup that later steps use to pick time zones.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.source_layout import Sources


def _select(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    return frame[list(mapping)].rename(columns=mapping).reset_index(drop=True)


def conform_supplier(sources: Sources) -> pd.DataFrame:
    frame = _select(sources[layout.ERP_VENDORS], {
        "VENDOR_NO": "supplier_id", "NAME": "supplier_name", "COUNTRY_KEY": "country",
        "REGION": "region", "TIER": "tier", "CURRENCY": "currency",
    })
    return frame.astype({"supplier_id": str, "tier": int})


def conform_part(sources: Sources) -> pd.DataFrame:
    frame = _select(sources[layout.ERP_ITEMS], {
        "MATERIAL": "part_id", "DESCRIPTION": "description", "CATEGORY": "category",
        "FAMILY": "family", "BASE_UOM": "uom", "STD_COST_USD": "standard_cost_usd",
    })
    return frame.astype({"part_id": str, "standard_cost_usd": float})


def conform_plant(sources: Sources) -> pd.DataFrame:
    return _select(sources[layout.ERP_PLANTS], {
        "PLANT": "plant_id", "NAME": "plant_name", "COUNTRY": "country", "REGION": "region",
    }).astype({"plant_id": str})


def conform_customer(sources: Sources) -> pd.DataFrame:
    return _select(sources[layout.ERP_CUSTOMERS], {
        "SOLD_TO": "customer_id", "NAME": "customer_name", "SEGMENT": "segment",
        "COUNTRY": "country", "REGION": "region",
    }).astype({"customer_id": str})


def conform_supplier_part(sources: Sources) -> pd.DataFrame:
    frame = _select(sources[layout.ERP_INFO_RECORDS], {
        "VENDOR_NO": "supplier_id", "MATERIAL": "part_id", "NET_PRICE": "unit_price_local",
        "MIN_ORDER_QTY": "moq", "PLANNED_DELIV_DAYS": "contracted_lead_time_days",
    })
    return frame.astype({"unit_price_local": float, "moq": int, "contracted_lead_time_days": int})


def party_countries(supplier: pd.DataFrame, plant: pd.DataFrame, customer: pd.DataFrame) -> pd.Series:
    """Country of every canonical party id (suppliers, plants, customers)."""
    return pd.concat([
        supplier.set_index("supplier_id")["country"],
        plant.set_index("plant_id")["country"],
        customer.set_index("customer_id")["country"],
    ])
