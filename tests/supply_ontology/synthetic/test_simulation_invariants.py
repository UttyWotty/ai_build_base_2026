"""Physical and logical invariants of the simulated world.

Stock must balance week to week, nothing ships or arrives beyond what was ordered, and cancelled lines never move.
Event dates must be ordered sensibly: order before ship before delivery.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.synthetic.world import World

SUNDAY = 6


def week_end(dates: pd.Series) -> pd.Series:
    """Sunday of the week containing each date."""
    stamps = pd.to_datetime(dates)
    return stamps + pd.to_timedelta(SUNDAY - stamps.dt.weekday, unit="D")


def test_inventory_balances_every_week(small_world: World) -> None:
    t = small_world.tables
    snapshots = t["inventory_snapshot"].assign(snapshot_date=lambda f: pd.to_datetime(f["snapshot_date"]))
    receipts = t["receipt"].merge(t["purchase_order_line"][["po_line_id", "plant_id", "part_id"]], on="po_line_id")
    shipped = t["outbound_shipment_line"].merge(t["shipment"][["shipment_id", "ship_date"]], on="shipment_id").merge(
        t["sales_order_line"][["so_line_id", "plant_id", "part_id"]], on="so_line_id"
    )
    inflow = receipts.assign(snapshot_date=week_end(receipts["receipt_date"])).groupby(
        ["plant_id", "part_id", "snapshot_date"])["qty_received"].sum()
    outflow = shipped.assign(snapshot_date=week_end(shipped["ship_date"])).groupby(
        ["plant_id", "part_id", "snapshot_date"])["qty_shipped"].sum()
    frame = snapshots.set_index(["plant_id", "part_id", "snapshot_date"]).sort_index()
    frame["previous"] = frame.groupby(level=["plant_id", "part_id"])["qty_on_hand"].shift()
    frame["inflow"] = inflow.reindex(frame.index, fill_value=0)
    frame["outflow"] = outflow.reindex(frame.index, fill_value=0)
    checked = frame.dropna(subset=["previous"])
    assert (checked["previous"] + checked["inflow"] - checked["outflow"] == checked["qty_on_hand"]).all()
    assert (frame["qty_on_hand"] >= 0).all()


def test_nothing_moves_beyond_ordered_quantities(small_world: World) -> None:
    t = small_world.tables
    shipped = t["outbound_shipment_line"].groupby("so_line_id")["qty_shipped"].sum()
    lines = t["sales_order_line"].set_index("so_line_id")
    assert (shipped <= lines.loc[shipped.index, "qty_ordered"]).all()
    received = t["receipt"].groupby("po_line_id")["qty_received"].sum()
    po = t["purchase_order_line"].set_index("po_line_id")
    assert (received <= po.loc[received.index, "qty_ordered"]).all()


def test_cancelled_lines_never_move(small_world: World) -> None:
    t = small_world.tables
    cancelled_so = set(t["sales_order_line"].query("status == 'cancelled'")["so_line_id"])
    cancelled_po = set(t["purchase_order_line"].query("status == 'cancelled'")["po_line_id"])
    assert cancelled_so and cancelled_po
    assert not cancelled_so & set(t["outbound_shipment_line"]["so_line_id"])
    assert not cancelled_po & set(t["receipt"]["po_line_id"])


def test_status_matches_movements(small_world: World) -> None:
    t = small_world.tables
    lines = t["sales_order_line"].set_index("so_line_id")
    shipped = t["outbound_shipment_line"].groupby("so_line_id")["qty_shipped"].sum().reindex(lines.index, fill_value=0)
    closed = lines["status"] == "closed"
    assert (shipped[closed] == lines.loc[closed, "qty_ordered"]).all()
    assert (shipped[lines["status"] == "open"] < lines.loc[lines["status"] == "open", "qty_ordered"]).all()


def test_event_dates_are_ordered(small_world: World) -> None:
    t = small_world.tables
    ship = t["shipment"]
    delivered = ship.dropna(subset=["delivered_date"])
    assert (delivered["delivered_date"] >= delivered["ship_date"]).all()
    assert (ship["planned_delivery_date"] > ship["ship_date"]).all()
    outbound = t["outbound_shipment_line"].merge(ship[["shipment_id", "ship_date"]], on="shipment_id").merge(
        t["sales_order_line"][["so_line_id", "order_date"]], on="so_line_id"
    )
    assert (outbound["ship_date"] > outbound["order_date"]).all()
    receipts = t["receipt"].merge(t["purchase_order_line"][["po_line_id", "order_date"]], on="po_line_id")
    assert (receipts["receipt_date"] > receipts["order_date"]).all()
    assert (t["sales_order_line"]["committed_date"] >= t["sales_order_line"]["order_date"]).all()
