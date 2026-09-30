"""A tiny hand-built conformed world whose metric values are worked out by hand in the comments below.

Sales lines L1..L5 (L4 cancelled): on time by committed L1, L3, L5; by requested only L3; complete on first shipment L1, L3, L5.
Expected: otd 3/4, by region NA 2/3 and EU 1/1, by month Jan 1.0, Feb 0.0, Mar 1.0; otd_vs_request 1/4; fill_rate 25/29; line_fill_rate 3/4; order_fill_rate 2/3.
PO lines: supplier_otd 2/3 (V1 1/2, V2 1/1). Shipments: carrier_on_time 1/3. Receipts: landed 480/40 = 12.0, purchase 400/40 = 10.0.
Inventory: days_of_inventory at the last snapshot 2026-02-01 is (60+30+20)/(5+5+0) = 11.0; January's last snapshot gives (80+40)/(10+10) = 6.0.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from supply_ontology.core.enums import AttributeType
from supply_ontology.core.ontology_model import Ontology

AS_OF = date(2026, 3, 31)


def d(month: int, day: int) -> date:
    return date(2026, month, day)


ROWS: dict[str, list[dict[str, object]]] = {
    "plant": [{"plant_id": "US01", "country": "US", "region": "NA"}, {"plant_id": "DE01", "country": "DE", "region": "EU"}],
    "customer": [{"customer_id": "C1", "region": "NA"}, {"customer_id": "C2", "region": "EU"}],
    "part": [{"part_id": "P1", "category": "Bearings"}, {"part_id": "P2", "category": "Fasteners"}, {"part_id": "P3", "category": "Castings"}],
    "supplier": [{"supplier_id": "V1", "country": "DE"}, {"supplier_id": "V2", "country": "US"}],
    "sales_order": [
        {"so_id": "O1", "customer_id": "C1", "status": "open", "first_ship_date": d(1, 5), "is_complete_on_first_shipment": False},
        {"so_id": "O2", "customer_id": "C2", "status": "closed", "first_ship_date": d(1, 15), "is_complete_on_first_shipment": True},
        {"so_id": "O3", "customer_id": "C1", "status": "open", "first_ship_date": d(3, 1), "is_complete_on_first_shipment": True},
    ],
    "sales_order_line": [
        {"so_line_id": "L1", "so_id": "O1", "part_id": "P1", "plant_id": "US01", "qty_ordered": 10, "status": "open",
         "requested_date": d(1, 8), "committed_date": d(1, 10), "first_ship_date": d(1, 5), "qty_on_first_shipment": 10,
         "is_complete_on_first_shipment": True, "is_delivered_complete_by_committed": True, "is_delivered_complete_by_requested": False},
        {"so_line_id": "L2", "so_id": "O1", "part_id": "P2", "plant_id": "US01", "qty_ordered": 10, "status": "open",
         "requested_date": d(2, 10), "committed_date": d(2, 10), "first_ship_date": d(2, 1), "qty_on_first_shipment": 6,
         "is_complete_on_first_shipment": False, "is_delivered_complete_by_committed": False, "is_delivered_complete_by_requested": False},
        {"so_line_id": "L3", "so_id": "O2", "part_id": "P1", "plant_id": "US01", "qty_ordered": 5, "status": "closed",
         "requested_date": d(1, 25), "committed_date": d(1, 20), "first_ship_date": d(1, 15), "qty_on_first_shipment": 5,
         "is_complete_on_first_shipment": True, "is_delivered_complete_by_committed": True, "is_delivered_complete_by_requested": True},
        {"so_line_id": "L4", "so_id": "O3", "part_id": "P2", "plant_id": "DE01", "qty_ordered": 8, "status": "cancelled",
         "requested_date": d(2, 15), "committed_date": d(2, 15), "first_ship_date": None, "qty_on_first_shipment": 0,
         "is_complete_on_first_shipment": False, "is_delivered_complete_by_committed": False, "is_delivered_complete_by_requested": False},
        {"so_line_id": "L5", "so_id": "O3", "part_id": "P1", "plant_id": "DE01", "qty_ordered": 4, "status": "open",
         "requested_date": d(3, 1), "committed_date": d(3, 5), "first_ship_date": d(3, 1), "qty_on_first_shipment": 4,
         "is_complete_on_first_shipment": True, "is_delivered_complete_by_committed": True, "is_delivered_complete_by_requested": False},
    ],
    "purchase_order_line": [
        {"po_line_id": "PL1", "supplier_id": "V1", "part_id": "P1", "plant_id": "US01", "promised_date": d(1, 10), "status": "closed", "is_received_complete_by_promised": True},
        {"po_line_id": "PL2", "supplier_id": "V1", "part_id": "P2", "plant_id": "US01", "promised_date": d(2, 10), "status": "open", "is_received_complete_by_promised": False},
        {"po_line_id": "PL3", "supplier_id": "V2", "part_id": "P3", "plant_id": "DE01", "promised_date": d(1, 20), "status": "closed", "is_received_complete_by_promised": True},
        {"po_line_id": "PL4", "supplier_id": "V2", "part_id": "P3", "plant_id": "DE01", "promised_date": d(1, 25), "status": "cancelled", "is_received_complete_by_promised": False},
    ],
    "shipment": [
        {"shipment_id": "S1", "direction": "inbound", "planned_delivery_date": d(1, 3), "delivered_date": d(1, 3), "is_delivered_by_planned": True},
        {"shipment_id": "S2", "direction": "outbound", "planned_delivery_date": d(1, 4), "delivered_date": d(1, 6), "is_delivered_by_planned": False},
        {"shipment_id": "S3", "direction": "outbound", "planned_delivery_date": d(2, 1), "delivered_date": None, "is_delivered_by_planned": False},
    ],
    "receipt": [
        {"receipt_id": "R1", "po_line_id": "PL1", "inbound_shipment_id": "S1", "qty_received": 10, "receipt_date": d(1, 3), "goods_value_usd": 100.0, "landed_cost_usd": 150.0},
        {"receipt_id": "R2", "po_line_id": "PL3", "inbound_shipment_id": "S1", "qty_received": 30, "receipt_date": d(1, 20), "goods_value_usd": 300.0, "landed_cost_usd": 330.0},
    ],
    "inventory_snapshot": [
        {"plant_id": "US01", "part_id": "P1", "snapshot_date": d(1, 4), "on_hand_value_usd": 100.0, "trailing_daily_cogs_usd": 10.0},
        {"plant_id": "US01", "part_id": "P1", "snapshot_date": d(1, 11), "on_hand_value_usd": 80.0, "trailing_daily_cogs_usd": 10.0},
        {"plant_id": "US01", "part_id": "P1", "snapshot_date": d(2, 1), "on_hand_value_usd": 60.0, "trailing_daily_cogs_usd": 5.0},
        {"plant_id": "US01", "part_id": "P2", "snapshot_date": d(1, 4), "on_hand_value_usd": 50.0, "trailing_daily_cogs_usd": 5.0},
        {"plant_id": "US01", "part_id": "P2", "snapshot_date": d(1, 11), "on_hand_value_usd": 40.0, "trailing_daily_cogs_usd": 10.0},
        {"plant_id": "US01", "part_id": "P2", "snapshot_date": d(2, 1), "on_hand_value_usd": 30.0, "trailing_daily_cogs_usd": 5.0},
        {"plant_id": "DE01", "part_id": "P3", "snapshot_date": d(2, 1), "on_hand_value_usd": 20.0, "trailing_daily_cogs_usd": 0.0},
    ],
}


def golden_frames(ontology: Ontology) -> dict[str, pd.DataFrame]:
    """One frame per populated entity with every ontology column; unspecified columns are null, dates are typed."""
    frames = {}
    for name, rows in ROWS.items():
        entity = ontology.entities[name]
        frame = pd.DataFrame(rows).reindex(columns=list(entity.attributes))
        for attribute in entity.attributes.values():
            if attribute.data_type == AttributeType.DATE:
                frame[attribute.name] = pd.to_datetime(frame[attribute.name])
        frames[name] = frame
    return frames
