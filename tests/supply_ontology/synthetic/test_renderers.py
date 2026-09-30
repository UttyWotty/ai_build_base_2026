"""Round-trip tests for the source renderers: each deliberate inconsistency must be resolvable back to the truth.

These tests encode exactly what the conform pipeline will have to do, so they double as its specification.
They also confirm the traps exist (for example UTC dates that differ from local dates).
"""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd

from supply_ontology.data_pipeline.synthetic.reference_data import COUNTRIES
from supply_ontology.data_pipeline.synthetic.render_portal import portal_name
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.utc_timestamps import local_to_utc_strings
from supply_ontology.data_pipeline.synthetic.world import World


def _sources(world: World) -> dict[str, pd.DataFrame]:
    return {source.relative_path: source.frame for source in render_sources(world)}


def test_latest_portal_confirmation_is_the_promised_date(small_world: World) -> None:
    portal = _sources(small_world)["supplier_portal/confirmations.xlsx"]
    latest = portal.sort_values("Confirmed At").groupby(["PO Number", "Line"]).last().reset_index()
    latest["po_line_id"] = latest["PO Number"] + "-" + latest["Line"].map("{:05d}".format)
    latest["promised"] = pd.to_datetime(latest["Confirmed Delivery"], format="%d/%m/%Y").dt.date
    truth = small_world.tables["purchase_order_line"].query("status != 'cancelled'").set_index("po_line_id")
    assert (latest.set_index("po_line_id")["promised"].reindex(truth.index) == truth["promised_date"]).all()


def test_tms_pickup_converts_back_to_the_local_ship_date(small_world: World) -> None:
    sources = _sources(small_world)
    tms = sources["tms/shipments.parquet"]
    crosswalk = sources["mdm/partner_crosswalk.xlsx"].set_index("PARTNER_CODE")["ERP_NUMBER"]
    countries = pd.concat([
        small_world.tables[e].set_index(k)["country"] for e, k in
        (("supplier", "supplier_id"), ("customer", "customer_id"), ("plant", "plant_id"))
    ])
    origin_zone = tms["ORIGIN_PARTNER"].map(crosswalk).map(countries).map(lambda c: COUNTRIES[c].timezone)
    utc = pd.to_datetime(tms["PICKUP_TS_UTC"], utc=True)
    local_dates = [ts.astimezone(ZoneInfo(zone)).date() for ts, zone in zip(utc, origin_zone)]
    truth = small_world.tables["shipment"].set_index("shipment_id").loc[tms["TMS_REF"], "ship_date"]
    assert list(truth) == local_dates
    assert (utc.dt.date.to_numpy() != truth.to_numpy()).any(), "expected some UTC dates to differ from local dates"


def test_tms_quantities_convert_back_from_cases(small_world: World) -> None:
    sources = _sources(small_world)
    lines = sources["tms/outbound_lines.parquet"]
    pack = sources["erp/item_master.xlsx"].set_index("MATERIAL")["CASE_PACK"]
    material = "P-" + lines["ITEM_CODE"]
    each = lines["QTY"] * material.map(pack).where(lines["UOM"] == "CS", 1)
    so_number, item = lines["ORDER_REF"].str.split("/").str[0], lines["ORDER_REF"].str.split("/").str[1].astype(int)
    key = pd.DataFrame({"shipment_id": lines["TMS_REF"], "so_line_id": so_number + "-" + item.map("{:03d}".format)})
    truth = small_world.tables["outbound_shipment_line"].set_index(["shipment_id", "so_line_id"])["qty_shipped"]
    assert (each.to_numpy() == truth.loc[list(zip(key["shipment_id"], key["so_line_id"]))].to_numpy()).all()
    assert (lines["UOM"] == "CS").any()


def test_receipts_link_to_shipments_by_bill_of_lading(small_world: World) -> None:
    sources = _sources(small_world)
    tms_ref_of = sources["tms/shipments.parquet"].set_index("BOL_NUMBER")["TMS_REF"]
    receipts = sources["erp/goods_receipts.parquet"]
    truth = small_world.tables["receipt"].set_index("receipt_id")["inbound_shipment_id"]
    assert (receipts["BILL_OF_LADING"].map(tms_ref_of).to_numpy() == truth.loc[receipts["MAT_DOC"]].to_numpy()).all()


def test_reference_feeds_invert_to_canonical_values(small_world: World) -> None:
    sources = _sources(small_world)
    fx = sources["treasury/fx_rates.xlsx"]
    truth_fx = small_world.tables["fx_rate"]
    assert ((1.0 / fx["Rate per USD"]).to_numpy() == truth_fx["usd_per_unit"].to_numpy()).all()
    duty = sources["trade/duty_rates.xlsx"]
    assert ((duty["Duty %"] / 100.0).to_numpy() == small_world.tables["duty_rate"]["duty_pct"].to_numpy()).all()


def test_portal_names_differ_from_erp_names() -> None:
    assert portal_name("Apex Precision GmbH", 1) == "Apex Precision Gmbh."
    assert portal_name("Helix Components Co., Ltd.", 3) == "HELIX COMPONENTS CO LTD"
    assert portal_name("Summit Industrial Inc.", 2) == "Summit Industrial Incorporated"


def test_utc_conversion_crosses_midnight_for_eastern_zones() -> None:
    days = pd.Series([date(2025, 3, 5), None])
    utc = local_to_utc_strings(days, pd.Series([6, 6]), pd.Series(["Asia/Shanghai", "Asia/Shanghai"]))
    assert list(utc) == ["2025-03-04T22:00:00Z", None]
