"""Checks that each planted story is visible in the small world's truth tables.

The measures here are deliberately simple pandas calculations, independent of the future metric compiler.
Thresholds are loose enough to hold for any seed but tight enough to fail if a story is switched off.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.synthetic.world import World
from tests.supply_ontology.conftest import SMALL_CONFIG

STORIES = SMALL_CONFIG.stories
START = pd.Timestamp(SMALL_CONFIG.horizon_start)


def _week(dates: pd.Series) -> pd.Series:
    return (pd.to_datetime(dates) - START).dt.days // 7


def _supplier_on_time(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    po = t["purchase_order_line"].query("status != 'cancelled'")
    receipts = t["receipt"].merge(po[["po_line_id", "qty_ordered"]], on="po_line_id").sort_values(["po_line_id", "receipt_date"])
    receipts["cumulative"] = receipts.groupby("po_line_id")["qty_received"].cumsum()
    complete = receipts[receipts["cumulative"] >= receipts["qty_ordered"]].groupby("po_line_id")["receipt_date"].first()
    po = po.assign(completed=po["po_line_id"].map(complete))
    return po.dropna(subset=["completed"]).assign(
        on_time=lambda f: f["completed"] <= f["promised_date"], week=lambda f: _week(f["promised_date"])
    )


def test_degrading_supplier_loses_on_time_share(small_world: World) -> None:
    lines = _supplier_on_time(small_world.tables)
    story = lines[lines["supplier_id"] == small_world.story_facts.degrading_supplier_id]
    before = story[story["week"] < STORIES.degradation_start_week]["on_time"].mean()
    after = story[story["week"] >= STORIES.degradation_start_week + STORIES.degradation_weeks]["on_time"].mean()
    peers = lines[lines["supplier_id"] != small_world.story_facts.degrading_supplier_id]["on_time"].mean()
    assert before - after > 0.12
    assert after < peers - 0.1


def test_freight_spikes_on_the_story_lane(small_world: World) -> None:
    t = small_world.tables
    country = t["supplier"].set_index("supplier_id")["country"]
    inbound = t["shipment"].query("direction == 'inbound'")
    lane = inbound[(inbound["origin"].map(country) == STORIES.freight_spike_origin_country)
                   & (inbound["destination"] == STORIES.freight_spike_plant_id)]
    week = _week(lane["ship_date"])
    window = (week >= STORIES.freight_spike_start_week) & (week < STORIES.freight_spike_start_week + STORIES.freight_spike_weeks)
    assert lane[window]["freight_cost_usd"].mean() > 1.5 * lane[~window]["freight_cost_usd"].mean()


def test_overstock_plant_category_holds_more_days_of_stock(small_world: World) -> None:
    t = small_world.tables
    part = t["part"].set_index("part_id")
    stock = t["inventory_snapshot"].assign(
        value=lambda f: f["qty_on_hand"] * f["part_id"].map(part["standard_cost_usd"]),
        category=lambda f: f["part_id"].map(part["category"]),
    )
    shipped = t["outbound_shipment_line"].merge(t["sales_order_line"][["so_line_id", "plant_id", "part_id"]], on="so_line_id")
    shipped = shipped.assign(
        cogs=shipped["qty_shipped"] * shipped["part_id"].map(part["standard_cost_usd"]),
        category=shipped["part_id"].map(part["category"]),
    )
    keys = ["plant_id", "category"]
    days = stock.groupby(keys + ["snapshot_date"])["value"].sum().groupby(keys).mean() / (
        shipped.groupby(keys)["cogs"].sum() / (SMALL_CONFIG.scale.weeks * 7)
    )
    story = days.loc[(STORIES.overstock_plant_id, STORIES.overstock_category)]
    assert story > 2.5 * days.drop((STORIES.overstock_plant_id, STORIES.overstock_category)).median()


def test_short_requests_make_committed_dates_later(small_world: World) -> None:
    t = small_world.tables
    lines = t["sales_order_line"].merge(t["sales_order"][["so_id", "customer_id"]], on="so_id")
    segment = lines["customer_id"].map(t["customer"].set_index("customer_id")["segment"])
    later = lines["committed_date"] > lines["requested_date"]
    short = later[segment == STORIES.short_request_segment].mean()
    others = later[segment != STORIES.short_request_segment].mean()
    assert short - others > 0.35
