"""Hand-computed checks of every derived attribute definition on tiny frames.

Each test builds the smallest input that exercises one rule from semantic/ontology.yaml, including edge cases.
Expected values are written out by hand so the definitions, not the implementation, are the reference.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from supply_ontology.data_pipeline.conform.completion import completion_dates
from supply_ontology.data_pipeline.conform.derived_inventory import add_inventory_values
from supply_ontology.data_pipeline.conform.derived_procurement import (
    add_po_line_rollups,
    add_receipt_costs,
)
from supply_ontology.data_pipeline.conform.derived_sales import (
    add_sales_line_rollups,
    add_sales_order_rollups,
    add_shipment_flags,
)

D = date


def test_completion_date_is_when_cumulative_reaches_ordered() -> None:
    events = pd.DataFrame({"k": ["a", "a", "b"], "d": [D(2025, 1, 5), D(2025, 1, 2), D(2025, 1, 3)],
                           "q": [6, 4, 3], "id": ["2", "1", "3"]})
    ordered = pd.Series({"a": 10, "b": 5, "c": 1})
    result = completion_dates(events, "k", "d", "q", "id", ordered)
    assert result.to_dict() == {"a": D(2025, 1, 5), "b": None, "c": None}


def test_po_line_on_time_needs_full_quantity_by_promised() -> None:
    po = pd.DataFrame({"po_line_id": ["L1", "L2", "L3"], "qty_ordered": [10, 10, 10],
                       "promised_date": [D(2025, 1, 10)] * 3})
    receipts = pd.DataFrame({"receipt_id": ["R1", "R2", "R3", "R4"], "po_line_id": ["L1", "L2", "L2", "L3"],
                             "qty_received": [10, 6, 4, 5],
                             "receipt_date": [D(2025, 1, 10), D(2025, 1, 9), D(2025, 1, 11), D(2025, 1, 1)]})
    result = add_po_line_rollups(po, receipts).set_index("po_line_id")
    assert result["qty_received"].tolist() == [10, 10, 5]
    assert result["last_receipt_date"].tolist() == [D(2025, 1, 10), D(2025, 1, 11), None]
    assert result["is_received_complete_by_promised"].tolist() == [True, False, False]


def test_receipt_costs_allocate_freight_by_value_and_skip_domestic_duty() -> None:
    day = D(2025, 2, 1)
    receipts = pd.DataFrame({"receipt_id": ["R1", "R2"], "po_line_id": ["L1", "L2"], "inbound_shipment_id": ["S1", "S1"],
                             "qty_received": [10, 30], "receipt_date": [day, day]})
    po = pd.DataFrame({"po_line_id": ["L1", "L2"], "supplier_id": ["V1", "V2"], "part_id": ["P1", "P1"],
                       "plant_id": ["US01", "US01"], "unit_price_local": [2.0, 1.0], "currency": ["EUR", "USD"]})
    result = add_receipt_costs(
        receipts, po,
        part=pd.DataFrame({"part_id": ["P1"], "category": ["Bearings"]}),
        supplier=pd.DataFrame({"supplier_id": ["V1", "V2"], "country": ["DE", "US"]}),
        plant=pd.DataFrame({"plant_id": ["US01"], "country": ["US"]}),
        shipment=pd.DataFrame({"shipment_id": ["S1"], "freight_cost_usd": [100.0]}),
        fx_rate=pd.DataFrame({"currency": ["EUR", "USD"], "rate_date": [day, day], "usd_per_unit": [1.5, 1.0]}),
        duty_rate=pd.DataFrame({"origin_country": ["DE", "US"], "category": ["Bearings", "Bearings"], "duty_pct": [0.1, 0.2]}),
    )
    assert result["goods_value_usd"].tolist() == [30.0, 30.0]
    assert result["freight_allocated_usd"].tolist() == [50.0, 50.0]
    assert result["duty_usd"].tolist() == [pytest.approx(3.0), 0.0]
    assert result["landed_cost_usd"].tolist() == [pytest.approx(83.0), 80.0]


def _sales_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lines = pd.DataFrame({"so_line_id": ["A", "B", "C"], "so_id": ["O1", "O1", "O2"], "qty_ordered": [10, 5, 4],
                          "status": ["open", "closed", "cancelled"],
                          "requested_date": [D(2025, 3, 5)] * 3, "committed_date": [D(2025, 3, 8)] * 3})
    shipments = pd.DataFrame({"shipment_id": ["S1", "S2", "S3"],
                              "ship_date": [D(2025, 3, 1), D(2025, 3, 4), D(2025, 3, 2)],
                              "planned_delivery_date": [D(2025, 3, 3), D(2025, 3, 7), D(2025, 3, 6)],
                              "delivered_date": [D(2025, 3, 3), None, D(2025, 3, 7)]})
    shipment_lines = pd.DataFrame({"shipment_id": ["S1", "S2", "S3"], "so_line_id": ["A", "A", "B"], "qty_shipped": [6, 4, 5]})
    return lines, shipment_lines, shipments


def test_sales_line_rollups_count_only_delivered_quantity() -> None:
    lines, shipment_lines, shipments = _sales_fixture()
    result = add_sales_line_rollups(lines, shipment_lines, shipments).set_index("so_line_id")
    assert result["qty_delivered"].tolist() == [6, 5, 0]
    assert result["last_delivery_date"].tolist() == [None, D(2025, 3, 7), None]
    assert result["first_ship_date"].tolist() == [D(2025, 3, 1), D(2025, 3, 2), None]
    assert result["qty_on_first_shipment"].tolist() == [6, 5, 0]
    assert result["is_complete_on_first_shipment"].tolist() == [False, True, False]
    assert result["is_delivered_complete_by_committed"].tolist() == [False, True, False]
    assert result["is_delivered_complete_by_requested"].tolist() == [False, False, False]


def test_sales_order_rollups_ignore_cancelled_lines() -> None:
    lines, shipment_lines, shipments = _sales_fixture()
    rolled = add_sales_line_rollups(lines, shipment_lines, shipments)
    orders = pd.DataFrame({"so_id": ["O1", "O2"]})
    result = add_sales_order_rollups(orders, rolled).set_index("so_id")
    assert result["first_ship_date"].tolist() == [D(2025, 3, 1), None]
    assert result["is_complete_on_first_shipment"].tolist() == [False, False]


def test_shipment_in_transit_is_not_on_time() -> None:
    _, _, shipments = _sales_fixture()
    assert add_shipment_flags(shipments)["is_delivered_by_planned"].tolist() == [True, False, False]


def test_trailing_cogs_window_includes_snapshot_day_and_excludes_older_days() -> None:
    snapshot_day = D(2025, 4, 30)
    snapshots = pd.DataFrame({"plant_id": ["US01", "US01"], "part_id": ["P1", "P2"],
                              "snapshot_date": [snapshot_day, snapshot_day], "qty_on_hand": [7, 0]})
    part = pd.DataFrame({"part_id": ["P1", "P2"], "standard_cost_usd": [2.0, 5.0]})
    shipments = pd.DataFrame({"shipment_id": ["S1", "S2", "S3"],
                              "ship_date": [D(2025, 4, 30), D(2025, 4, 21), D(2025, 4, 20)]})
    shipment_lines = pd.DataFrame({"shipment_id": ["S1", "S2", "S3"], "so_line_id": ["A", "A", "A"], "qty_shipped": [1, 2, 100]})
    sales_lines = pd.DataFrame({"so_line_id": ["A"], "plant_id": ["US01"], "part_id": ["P1"]})
    result = add_inventory_values(snapshots, part, shipment_lines, shipments, sales_lines, window_days=10)
    assert result["on_hand_value_usd"].tolist() == [14.0, 0.0]
    assert result["trailing_daily_cogs_usd"].tolist() == [pytest.approx((1 + 2) * 2.0 / 10), 0.0]
