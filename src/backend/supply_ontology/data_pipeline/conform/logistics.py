"""Conforms TMS shipments and outbound lines into the shipment and outbound_shipment_line entities.

Partner codes resolve through the MDM crosswalk; UTC event times become local dates at the origin or destination party.
Freight converts to USD at the FX rate on the local ship date, and case quantities convert back to base units.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.country_timezones import COUNTRY_TIMEZONES
from supply_ontology.data_pipeline.conform.dates import utc_to_local_dates
from supply_ontology.data_pipeline.conform.errors import ConformError
from supply_ontology.data_pipeline.conform.keys import (
    SO_ITEM_WIDTH,
    composite_id,
    map_or_fail,
)
from supply_ontology.data_pipeline.conform.reference import usd_rates_on
from supply_ontology.data_pipeline.conform.source_layout import Sources

TMS_DIRECTION = pd.Series({"IB": "inbound", "OB": "outbound"})
TMS_ORDER_SEPARATOR = "/"
ERP_PART_PREFIX = "P-"
CASE_UOM, EACH_UOM = "CS", "EA"
SHIPMENT_LINE_PREFIX = "SL"
SHIPMENT_LINE_WIDTH = 8


def partner_crosswalk(sources: Sources) -> pd.Series:
    """TMS partner code -> canonical party id; every code must be unique."""
    crosswalk = sources[layout.MDM_CROSSWALK]
    if crosswalk["PARTNER_CODE"].duplicated().any():
        raise ConformError("Partner crosswalk maps a partner code more than once")
    return crosswalk.set_index("PARTNER_CODE")["ERP_NUMBER"].astype(str)


def conform_shipment(sources: Sources, countries: pd.Series, fx_rate: pd.DataFrame) -> pd.DataFrame:
    tms = sources[layout.TMS_SHIPMENTS]
    crosswalk = partner_crosswalk(sources)
    origin = map_or_fail(tms["ORIGIN_PARTNER"], crosswalk, "shipment origin partner")
    destination = map_or_fail(tms["DEST_PARTNER"], crosswalk, "shipment destination partner")
    zones = pd.Series(COUNTRY_TIMEZONES)
    origin_zone = map_or_fail(map_or_fail(origin, countries, "origin party country"), zones, "origin time zone")
    destination_zone = map_or_fail(map_or_fail(destination, countries, "destination party country"), zones, "destination time zone")
    ship_date = utc_to_local_dates(tms["PICKUP_TS_UTC"], origin_zone)
    rates = usd_rates_on(fx_rate, tms["FREIGHT_CCY"], ship_date)
    return pd.DataFrame({
        "shipment_id": tms["TMS_REF"].astype(str),
        "direction": map_or_fail(tms["DIRECTION"], TMS_DIRECTION, "shipment direction code"),
        "carrier": tms["CARRIER_SCAC"],
        "origin": origin,
        "destination": destination,
        "ship_date": ship_date,
        "planned_delivery_date": utc_to_local_dates(tms["PLANNED_DELIVERY_TS_UTC"], destination_zone),
        "delivered_date": utc_to_local_dates(tms["DELIVERED_TS_UTC"], destination_zone),
        "freight_cost_usd": tms["FREIGHT_AMOUNT"].astype(float) * rates,
    })


def conform_outbound_shipment_line(sources: Sources) -> pd.DataFrame:
    """Shipment lines with a surrogate id minted in (shipment_id, so_line_id) order."""
    tms = sources[layout.TMS_OUTBOUND_LINES]
    order_ref = tms["ORDER_REF"].str.split(TMS_ORDER_SEPARATOR, n=1)
    part_id = ERP_PART_PREFIX + tms["ITEM_CODE"].astype(str)
    case_pack = map_or_fail(part_id, sources[layout.ERP_ITEMS].set_index("MATERIAL")["CASE_PACK"], "item case pack")
    unknown_uom = ~tms["UOM"].isin([CASE_UOM, EACH_UOM])
    if unknown_uom.any():
        raise ConformError(f"Unknown TMS units of measure: {tms.loc[unknown_uom, 'UOM'].unique().tolist()}")
    qty = tms["QTY"].astype(float) * case_pack.where(tms["UOM"] == CASE_UOM, 1)
    frame = pd.DataFrame({
        "shipment_id": tms["TMS_REF"].astype(str),
        "so_line_id": composite_id(order_ref.str[0], order_ref.str[1], SO_ITEM_WIDTH),
        "qty_shipped": qty.round().astype(int),
    }).sort_values(["shipment_id", "so_line_id"], kind="mergesort").reset_index(drop=True)
    frame.insert(0, "shipment_line_id", [f"{SHIPMENT_LINE_PREFIX}{i + 1:0{SHIPMENT_LINE_WIDTH}d}" for i in range(len(frame))])
    return frame
