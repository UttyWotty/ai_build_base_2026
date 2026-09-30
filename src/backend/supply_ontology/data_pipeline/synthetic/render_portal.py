"""Renders supplier delivery confirmations as a supplier portal export.

Every confirmation and revision is a separate row; the latest by confirmation time is the promised date.
Supplier names are spelled the portal's way and dates use DD/MM/YYYY text, so joining on names or parsing dates naively fails.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.synthetic.reference_data import COUNTRIES
from supply_ontology.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from supply_ontology.data_pipeline.synthetic.utc_timestamps import local_to_utc_strings
from supply_ontology.data_pipeline.synthetic.world_tables import WorldExtras

PORTAL_DATE_FORMAT = "%d/%m/%Y"
ERP_ITEM_SEPARATOR = "-"
# Legal suffixes as the portal spells them.
PORTAL_SUFFIX_SPELLING = {
    "Inc.": "Incorporated", "S.A. de C.V.": "SA de CV", "GmbH": "Gmbh.", "Sp. z o.o.": "Sp z oo",
    "Co., Ltd.": "Co Ltd", "K.K.": "KK", "Pvt. Ltd.": "Private Limited",
}
# Every UPPERCASE_EVERY-th supplier is shown in upper case.
UPPERCASE_EVERY = 3


def portal_name(name: str, position: int) -> str:
    """Deterministic portal spelling of an ERP supplier name."""
    for erp_suffix, portal_suffix in PORTAL_SUFFIX_SPELLING.items():
        if name.endswith(erp_suffix):
            name = name[: -len(erp_suffix)] + portal_suffix
            break
    return name.upper() if position % UPPERCASE_EVERY == 0 else name


def render_portal(tables: dict[str, pd.DataFrame], extras: WorldExtras) -> list[SourceFile]:
    """Return the confirmations export."""
    supplier = tables["supplier"].reset_index(drop=True)
    names = {sid: portal_name(n, i) for i, (sid, n) in enumerate(zip(supplier["supplier_id"], supplier["supplier_name"]))}
    confirmations = extras.confirmations.merge(
        tables["purchase_order_line"][["po_line_id", "supplier_id"]], on="po_line_id", how="left"
    )
    country = confirmations["supplier_id"].map(supplier.set_index("supplier_id")["country"])
    parts = confirmations["po_line_id"].str.rsplit(ERP_ITEM_SEPARATOR, n=1)
    frame = pd.DataFrame({
        "PO Number": parts.str[0],
        "Line": parts.str[1].astype(int),
        "Supplier": confirmations["supplier_id"].map(names),
        "Confirmed Delivery": pd.to_datetime(confirmations["confirmed_date"].astype(str)).dt.strftime(PORTAL_DATE_FORMAT),
        "Confirmed At": local_to_utc_strings(
            confirmations["confirmed_at_date"], confirmations["confirmed_hour"],
            country.map(lambda c: COUNTRIES[c].timezone),
        ),
    })
    return [SourceFile("supplier_portal/confirmations.xlsx", frame, FileFormat.XLSX)]
