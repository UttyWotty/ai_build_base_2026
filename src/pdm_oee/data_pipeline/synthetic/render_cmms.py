"""Renders the CMMS export: work orders by asset number, with site-local times, type codes, and failure codes.

Some corrective orders were saved without a failure code (only the free text says what failed), some breakdowns
were entered twice, and closure dates can lag the repair by days; conform must survive all three.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.data_pipeline.synthetic.local_time import to_local
from pdm_oee.data_pipeline.synthetic.reference import FAILURE_CODES, WORK_TYPE_CODES
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from pdm_oee.data_pipeline.synthetic.work_orders import DUPLICATE_WO_NUMBER

DUPLICATE_TEXT = "Machine down, see other order"
EMPTY_CODE = ""


def render_cmms(tables: dict[str, pd.DataFrame], missing_code_ids: frozenset[str],
                duplicates: pd.DataFrame) -> list[SourceFile]:
    orders = tables["work_order"].merge(tables["asset"][["asset_id", "asset_number", "site_id"]], on="asset_id")
    frame = pd.DataFrame({
        "WO_NO": orders["wo_id"], "ASSET_NO": orders["asset_number"],
        "TYPE": orders["work_type"].map(WORK_TYPE_CODES),
        "FAILURE_CODE": [EMPTY_CODE if w in missing_code_ids or pd.isna(m) else FAILURE_CODES[m]
                         for w, m in zip(orders["wo_id"], orders["failure_mode"])],
        "DESCRIPTION": orders["description"],
        "CREATED": to_local(orders["created_at"], orders["site_id"]),
        "STARTED": to_local(orders["started_at"], orders["site_id"]),
        "COMPLETED": to_local(orders["closed_at"], orders["site_id"]),
        "DUE_DATE": orders["due_date"], "LABOUR_HOURS": orders["labour_hours"],
    })
    originals = frame.set_index("WO_NO")
    copies = []
    for number, row in enumerate(duplicates.itertuples(), start=DUPLICATE_WO_NUMBER):
        copy = originals.loc[row.original_wo_id].copy()
        copy["CREATED"] = copy["CREATED"] + pd.Timedelta(minutes=int(row.delay_minutes))
        copy["STARTED"] = copy["CREATED"]
        copy["FAILURE_CODE"], copy["DESCRIPTION"] = EMPTY_CODE, DUPLICATE_TEXT
        copies.append(copy.rename(str(number)))
    if copies:
        frame = pd.concat([frame, pd.DataFrame(copies).rename_axis("WO_NO").reset_index()], ignore_index=True)
    frame = frame.sort_values(["CREATED", "WO_NO"], kind="stable").reset_index(drop=True)
    return [SourceFile("cmms/work_orders.xlsx", frame, FileFormat.XLSX)]
