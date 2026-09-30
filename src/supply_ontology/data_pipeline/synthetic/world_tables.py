"""Assembles canonical truth tables (one per ontology entity) and renderer extras from simulation output.

Truth tables contain exactly the non-derived ontology attributes, in canonical formats, sorted by key.
Extras hold what only the source renderers need: confirmations, BOL numbers, local freight amounts, partner codes, and published rates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic import ids
from supply_ontology.data_pipeline.synthetic.inventory_sim import SimRecords
from supply_ontology.data_pipeline.synthetic.masters import Masters
from supply_ontology.data_pipeline.synthetic.timeline import Timeline, offsets_to_dates

STATUS_OPEN, STATUS_CLOSED, STATUS_CANCELLED = "open", "closed", "cancelled"
SUPPLIER_PARTNER, CUSTOMER_PARTNER, PLANT_PARTNER = "supplier", "customer", "plant"


@dataclass(frozen=True)
class WorldExtras:
    """Generator-side facts that source systems expose but the ontology does not model."""

    part_case_packs: pd.DataFrame
    confirmations: pd.DataFrame
    shipment_details: pd.DataFrame
    fx_published: pd.DataFrame
    duty_published: pd.DataFrame
    partner_codes: pd.DataFrame


def number_purchase_orders(records: SimRecords, masters: Masters) -> pd.DataFrame:
    """Group PO lines placed by one supplier for one plant on one day into a purchase order and number them."""
    lines = pd.DataFrame(
        records.po_lines,
        columns=["po_seq", "plant_id", "part_id", "supplier_id", "qty", "order_day", "promised_day", "cancelled"],
    ).sort_values(["order_day", "supplier_id", "plant_id", "po_seq"], kind="mergesort").reset_index(drop=True)
    order_index = pd.factorize(lines["order_day"].astype(str) + "|" + lines["supplier_id"] + "|" + lines["plant_id"])[0]
    line_number = (lines.groupby(order_index).cumcount() + 1) * ids.PO_LINE_STEP
    lines["po_id"] = [ids.po_number(i) for i in order_index]
    lines["po_line_id"] = [ids.po_line_id(po, int(n)) for po, n in zip(lines["po_id"], line_number)]
    contract = masters.supplier_parts.set_index(["supplier_id", "part_id"])["unit_price_local"]
    lines["unit_price_local"] = contract.loc[list(zip(lines["supplier_id"], lines["part_id"]))].to_numpy()
    lines["currency"] = lines["supplier_id"].map(masters.suppliers.set_index("supplier_id")["currency"])
    return lines


def number_receipts(records: SimRecords, po_lines: pd.DataFrame) -> pd.DataFrame:
    """Number receipts in booking order and attach their PO line context."""
    receipts = pd.DataFrame(records.receipts, columns=["po_seq", "receipt_day", "qty"])
    receipts = receipts.sort_values(["receipt_day", "po_seq", "qty"], kind="mergesort").reset_index(drop=True)
    receipts["receipt_id"] = [ids.receipt_id(i) for i in range(len(receipts))]
    context = po_lines.set_index("po_seq")[["po_line_id", "supplier_id", "plant_id", "part_id"]]
    return receipts.join(context, on="po_seq")


def assemble_world(
    *, masters: Masters, timeline: Timeline, sales_lines: pd.DataFrame, po_lines: pd.DataFrame,
    receipts: pd.DataFrame, allocations: pd.DataFrame, shipments: pd.DataFrame, confirmations: pd.DataFrame,
    snapshots: pd.DataFrame, fx_published: pd.DataFrame, duty: pd.DataFrame, rng: np.random.Generator,
) -> tuple[dict[str, pd.DataFrame], WorldExtras]:
    """Build every truth table and the renderer extras."""
    start = timeline.start
    shipments = _number_shipments(shipments)
    shipment_id_of = shipments.set_index("shipment_key")["shipment_id"]
    tables = {
        "plant": masters.plants.copy(),
        "supplier": masters.suppliers.copy(),
        "part": masters.parts.drop(columns=["case_pack"]),
        "customer": masters.customers.copy(),
        "supplier_part": masters.supplier_parts.copy(),
        "purchase_order_line": _po_line_table(po_lines, receipts, start),
        "receipt": _receipt_table(receipts, shipment_id_of, start),
        **_sales_tables(sales_lines, allocations, start),
        "shipment": _shipment_table(shipments, start),
        "outbound_shipment_line": _shipment_line_table(allocations, shipment_id_of),
        "inventory_snapshot": _inventory_table(snapshots, start),
        "fx_rate": _fx_table(fx_published, start),
        "duty_rate": duty[["origin_country", "category", "duty_pct"]].copy(),
    }
    extras = WorldExtras(
        part_case_packs=masters.parts[["part_id", "case_pack"]].copy(),
        confirmations=_confirmation_extras(confirmations, po_lines, start),
        shipment_details=_shipment_extras(shipments, start),
        fx_published=fx_published.assign(rate_date=offsets_to_dates(start, fx_published["day"]))[["currency", "rate_date", "units_per_usd"]],
        duty_published=duty[["origin_country", "category", "duty_rate_pct"]].copy(),
        partner_codes=_partner_codes(masters, rng),
    )
    return tables, extras


def _status(ordered: pd.Series, done: pd.Series, cancelled: pd.Series) -> np.ndarray:
    return np.where(cancelled, STATUS_CANCELLED, np.where(done >= ordered, STATUS_CLOSED, STATUS_OPEN))


def _po_line_table(po_lines: pd.DataFrame, receipts: pd.DataFrame, start: date) -> pd.DataFrame:
    received = po_lines["po_line_id"].map(receipts.groupby("po_line_id")["qty"].sum()).fillna(0)
    table = pd.DataFrame({
        "po_line_id": po_lines["po_line_id"], "po_id": po_lines["po_id"], "supplier_id": po_lines["supplier_id"],
        "part_id": po_lines["part_id"], "plant_id": po_lines["plant_id"], "qty_ordered": po_lines["qty"],
        "unit_price_local": po_lines["unit_price_local"], "currency": po_lines["currency"],
        "order_date": offsets_to_dates(start, po_lines["order_day"]),
        "promised_date": offsets_to_dates(start, po_lines["promised_day"]),
        "status": _status(po_lines["qty"], received, po_lines["cancelled"]),
    })
    return table.sort_values("po_line_id").reset_index(drop=True)


def _receipt_table(receipts: pd.DataFrame, shipment_id_of: pd.Series, start: date) -> pd.DataFrame:
    return pd.DataFrame({
        "receipt_id": receipts["receipt_id"], "po_line_id": receipts["po_line_id"],
        "inbound_shipment_id": receipts["shipment_key"].map(shipment_id_of),
        "qty_received": receipts["qty"], "receipt_date": offsets_to_dates(start, receipts["receipt_day"]),
    })


def _sales_tables(sales_lines: pd.DataFrame, allocations: pd.DataFrame, start: date) -> dict[str, pd.DataFrame]:
    shipped = sales_lines["so_line_id"].map(allocations.groupby("so_line_id")["qty"].sum()).fillna(0)
    line_status = _status(sales_lines["qty_ordered"], shipped, sales_lines["cancelled"])
    lines = pd.DataFrame({
        "so_line_id": sales_lines["so_line_id"], "so_id": sales_lines["so_id"], "part_id": sales_lines["part_id"],
        "plant_id": sales_lines["plant_id"], "qty_ordered": sales_lines["qty_ordered"],
        "order_date": offsets_to_dates(start, sales_lines["order_day"]),
        "requested_date": offsets_to_dates(start, sales_lines["requested_day"]),
        "committed_date": offsets_to_dates(start, sales_lines["committed_day"]),
        "status": line_status,
    })
    header = sales_lines.assign(status=line_status).groupby("so_id", sort=True).agg(
        customer_id=("customer_id", "first"), order_day=("order_day", "first"),
        all_cancelled=("status", lambda s: bool((s == STATUS_CANCELLED).all())),
        all_done=("status", lambda s: bool(s.isin([STATUS_CLOSED, STATUS_CANCELLED]).all())),
    ).reset_index()
    header_status = np.where(header["all_cancelled"], STATUS_CANCELLED, np.where(header["all_done"], STATUS_CLOSED, STATUS_OPEN))
    orders = pd.DataFrame({
        "so_id": header["so_id"], "customer_id": header["customer_id"],
        "order_date": offsets_to_dates(start, header["order_day"]), "status": header_status,
    })
    return {"sales_order": orders, "sales_order_line": lines.sort_values("so_line_id").reset_index(drop=True)}


def _number_shipments(shipments: pd.DataFrame) -> pd.DataFrame:
    ordered = shipments.sort_values(
        ["ship_day", "direction", "origin", "destination", "shipment_key"], kind="mergesort"
    ).reset_index(drop=True)
    ordered["shipment_id"] = [ids.shipment_id(i) for i in range(len(ordered))]
    ordered["bol_number"] = [ids.bol_number(i) for i in range(len(ordered))]
    return ordered


def _shipment_table(shipments: pd.DataFrame, start: date) -> pd.DataFrame:
    return pd.DataFrame({
        "shipment_id": shipments["shipment_id"], "direction": shipments["direction"], "carrier": shipments["carrier"],
        "origin": shipments["origin"], "destination": shipments["destination"],
        "ship_date": offsets_to_dates(start, shipments["ship_day"]),
        "planned_delivery_date": offsets_to_dates(start, shipments["planned_delivery_day"]),
        "delivered_date": offsets_to_dates(start, shipments["delivered_day"].astype("Int64")),
        "freight_cost_usd": shipments["freight_cost_usd"].astype(float),
    })


def _shipment_line_table(allocations: pd.DataFrame, shipment_id_of: pd.Series) -> pd.DataFrame:
    table = pd.DataFrame({
        "shipment_id": allocations["shipment_key"].map(shipment_id_of),
        "so_line_id": allocations["so_line_id"], "qty_shipped": allocations["qty"],
    }).sort_values(["shipment_id", "so_line_id"], kind="mergesort").reset_index(drop=True)
    table.insert(0, "shipment_line_id", [ids.shipment_line_id(i) for i in range(len(table))])
    return table


def _inventory_table(snapshots: pd.DataFrame, start: date) -> pd.DataFrame:
    table = pd.DataFrame({
        "plant_id": snapshots["plant_id"], "part_id": snapshots["part_id"],
        "snapshot_date": offsets_to_dates(start, snapshots["day"]), "qty_on_hand": snapshots["qty_on_hand"],
    })
    return table.sort_values(["plant_id", "part_id", "snapshot_date"], kind="mergesort").reset_index(drop=True)


def _fx_table(fx_published: pd.DataFrame, start: date) -> pd.DataFrame:
    return pd.DataFrame({
        "currency": fx_published["currency"], "rate_date": offsets_to_dates(start, fx_published["day"]),
        "usd_per_unit": 1.0 / fx_published["units_per_usd"],
    })


def _confirmation_extras(confirmations: pd.DataFrame, po_lines: pd.DataFrame, start: date) -> pd.DataFrame:
    line_of = po_lines.set_index("po_seq")["po_line_id"]
    return pd.DataFrame({
        "po_line_id": confirmations["po_seq"].map(line_of),
        "confirmed_date": offsets_to_dates(start, confirmations["confirmed_day"]),
        "confirmed_at_date": offsets_to_dates(start, confirmations["confirmed_at_day"]),
        "confirmed_hour": confirmations["confirmed_hour"], "sequence": confirmations["sequence"],
    }).sort_values(["po_line_id", "sequence"], kind="mergesort").reset_index(drop=True)


def _shipment_extras(shipments: pd.DataFrame, start: date) -> pd.DataFrame:
    return shipments[[
        "shipment_id", "bol_number", "origin_country", "destination_country", "pickup_hour",
        "delivery_hour", "freight_amount_local", "freight_currency",
    ]].copy()


def _partner_codes(masters: Masters, rng: np.random.Generator) -> pd.DataFrame:
    """TMS partner codes, assigned in a shuffled order so they cannot be derived from ERP numbers."""
    supplier_order = rng.permutation(len(masters.suppliers))
    customer_order = rng.permutation(len(masters.customers))
    rows = [(ids.supplier_partner_code(i), SUPPLIER_PARTNER, masters.suppliers["supplier_id"].iloc[j]) for i, j in enumerate(supplier_order)]
    rows += [(ids.customer_partner_code(i), CUSTOMER_PARTNER, masters.customers["customer_id"].iloc[j]) for i, j in enumerate(customer_order)]
    rows += [(plant_id, PLANT_PARTNER, plant_id) for plant_id in masters.plants["plant_id"]]
    return pd.DataFrame(rows, columns=["partner_code", "partner_type", "canonical_id"])
