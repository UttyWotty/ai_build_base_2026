"""Renders shipments as a transport management system export with its own partner codes, units, and UTC timestamps.

Suppliers and customers appear as TMS partner codes, direction as IB/OB, part numbers without the ERP prefix, and case-packed parts in cases.
Event times are local times converted to UTC strings, so the UTC date can differ from the local shipping date.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.synthetic.logistics import INBOUND, OUTBOUND
from supply_ontology.data_pipeline.synthetic.reference_data import (
    CASE_UOM,
    COUNTRIES,
    EACH_UOM,
)
from supply_ontology.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from supply_ontology.data_pipeline.synthetic.utc_timestamps import local_to_utc_strings
from supply_ontology.data_pipeline.synthetic.world_tables import WorldExtras

TMS_DIRECTION_CODE = {INBOUND: "IB", OUTBOUND: "OB"}
ERP_PART_PREFIX = "P-"
ERP_ITEM_SEPARATOR = "-"
TMS_ORDER_SEPARATOR = "/"


def render_tms(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> list[SourceFile]:
    """Return the TMS shipment header and outbound line files."""
    return [_shipments(tables, extras), _outbound_lines(tables, extras)]


def _shipments(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> SourceFile:
    shipment = tables["shipment"].merge(extras.shipment_details, on="shipment_id", how="left")
    partner_of = extras.partner_codes.set_index("canonical_id")["partner_code"]
    origin_zone = shipment["origin_country"].map(lambda c: COUNTRIES[c].timezone)
    destination_zone = shipment["destination_country"].map(lambda c: COUNTRIES[c].timezone)
    frame = pd.DataFrame({
        "TMS_REF": shipment["shipment_id"],
        "DIRECTION": shipment["direction"].map(TMS_DIRECTION_CODE),
        "CARRIER_SCAC": shipment["carrier"],
        "ORIGIN_PARTNER": shipment["origin"].map(partner_of),
        "DEST_PARTNER": shipment["destination"].map(partner_of),
        "PICKUP_TS_UTC": local_to_utc_strings(shipment["ship_date"], shipment["pickup_hour"], origin_zone),
        "PLANNED_DELIVERY_TS_UTC": local_to_utc_strings(
            shipment["planned_delivery_date"], shipment["delivery_hour"], destination_zone
        ),
        "DELIVERED_TS_UTC": local_to_utc_strings(shipment["delivered_date"], shipment["delivery_hour"], destination_zone),
        "FREIGHT_AMOUNT": shipment["freight_amount_local"],
        "FREIGHT_CCY": shipment["freight_currency"],
        "BOL_NUMBER": shipment["bol_number"],
    })
    return SourceFile("tms/shipments.parquet", frame, FileFormat.PARQUET)


def _outbound_lines(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> SourceFile:
    lines = tables["outbound_shipment_line"].merge(
        tables["sales_order_line"][["so_line_id", "part_id"]], on="so_line_id", how="left"
    )
    case_pack = lines["part_id"].map(extras.part_case_packs.set_index("part_id")["case_pack"])
    in_cases = case_pack > 1
    so_number = lines["so_line_id"].str.rsplit(ERP_ITEM_SEPARATOR, n=1).str[0]
    item = lines["so_line_id"].str.rsplit(ERP_ITEM_SEPARATOR, n=1).str[1].astype(int)
    frame = pd.DataFrame({
        "TMS_REF": lines["shipment_id"],
        "ORDER_REF": so_number + TMS_ORDER_SEPARATOR + item.astype(str),
        "ITEM_CODE": lines["part_id"].str.removeprefix(ERP_PART_PREFIX),
        "QTY": (lines["qty_shipped"] / case_pack.where(in_cases, 1)).astype(float),
        "UOM": in_cases.map({True: CASE_UOM, False: EACH_UOM}),
    })
    return SourceFile("tms/outbound_lines.parquet", frame, FileFormat.PARQUET)
