"""Formatting of canonical and source-system identifiers.

Canonical ids follow ERP conventions; source renderers use the parse helpers to produce their own variants.
Keeping every format in one module means the conform pipeline has a single place to mirror.
"""
from __future__ import annotations

SUPPLIER_ID_BASE = 10001
CUSTOMER_ID_BASE = 20001
PO_NUMBER_BASE = 4500000001
RECEIPT_ID_BASE = 5000000001
SO_NUMBER_BASE = 100001
SHIPMENT_REF_BASE = 1
BOL_NUMBER_BASE = 70000001
SHIPMENT_LINE_BASE = 1
PO_LINE_STEP = 10
SO_ITEM_STEP = 10


def supplier_id(index: int) -> str:
    return f"V{SUPPLIER_ID_BASE + index}"


def customer_id(index: int) -> str:
    return f"C{CUSTOMER_ID_BASE + index}"


def part_id(index: int) -> str:
    return f"P-{index + 1:06d}"


def po_number(index: int) -> str:
    return str(PO_NUMBER_BASE + index)


def po_line_id(po: str, line_number: int) -> str:
    return f"{po}-{line_number:05d}"


def receipt_id(index: int) -> str:
    return str(RECEIPT_ID_BASE + index)


def so_number(index: int) -> str:
    return f"SO{SO_NUMBER_BASE + index}"


def so_line_id(so: str, item: int) -> str:
    return f"{so}-{item:03d}"


def shipment_id(index: int) -> str:
    return f"TMS{SHIPMENT_REF_BASE + index:07d}"


def bol_number(index: int) -> str:
    return f"BOL{BOL_NUMBER_BASE + index}"


def shipment_line_id(index: int) -> str:
    return f"SL{SHIPMENT_LINE_BASE + index:08d}"


def supplier_partner_code(index: int) -> str:
    return f"SUP-{index + 1:03d}"


def customer_partner_code(index: int) -> str:
    return f"CU-{index + 1:04d}"
