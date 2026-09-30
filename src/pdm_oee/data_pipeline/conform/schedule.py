"""Conforms the shift calendar and the production orders, converting their local times to UTC per site.

Shift ids combine the site, the shift date, and the shift letter, as the MES calendar states them.
Order lines are named "<site> Line <n>" in the ERP and become canonical line ids.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.local_clock import localize
from pdm_oee.data_pipeline.conform.masters import LINE_PATTERN
from pdm_oee.data_pipeline.conform.source_layout import (
    ERP_ORDERS,
    MES_CALENDAR,
    Sources,
)


def conform_shifts(sources: Sources, mappings: SourceMappings) -> pd.DataFrame:
    calendar = sources[MES_CALENDAR]
    frames = []
    for site_id, rows in calendar.groupby("SITE", sort=False):
        zone = mappings.sites[site_id].timezone
        dates = pd.to_datetime(rows["SHIFT_DATE"]).dt.date
        frames.append(pd.DataFrame({
            "shift_id": [f"{site_id}-{d.isoformat()}-{s}" for d, s in zip(dates, rows["SHIFT"])],
            "site_id": site_id, "shift_date": dates, "shift_letter": rows["SHIFT"],
            "planned_break_minutes": rows["BREAK_MINUTES"].astype(int),
            "start_at": localize(pd.to_datetime(rows["START_LOCAL"]), zone),
            "end_at": localize(pd.to_datetime(rows["END_LOCAL"]), zone)}))
    return pd.concat(frames).sort_values("start_at", kind="stable").reset_index(drop=True)


def conform_orders(sources: Sources, mappings: SourceMappings) -> pd.DataFrame:
    orders = sources[ERP_ORDERS]
    parsed = orders["LINE"].str.extract(LINE_PATTERN)
    frames = []
    for site_id, rows in orders.groupby(parsed["site"], sort=False):
        zone = mappings.sites[site_id].timezone
        frames.append(pd.DataFrame({
            "order_id": rows["ORDER_NO"], "line_id": site_id + "-L" + parsed.loc[rows.index, "line"],
            "product_id": rows["PRODUCT"], "quantity": rows["QTY"].astype(int),
            "planned_start_at": localize(pd.to_datetime(rows["START_LOCAL"]), zone),
            "planned_end_at": localize(pd.to_datetime(rows["END_LOCAL"]), zone)}))
    return pd.concat(frames).reset_index(drop=True)
