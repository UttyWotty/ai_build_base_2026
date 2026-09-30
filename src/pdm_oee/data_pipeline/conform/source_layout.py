"""The expected layout of the source exports: relative file paths and the columns conform relies on.

These constants describe the external systems as the conform step sees them; they never import the generator.
check_sources verifies every expected file and column before any transformation runs.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from pdm_oee.data_pipeline.conform.errors import ConformError

REGISTER_ASSETS = "asset_register/assets.xlsx"
REGISTER_SENSORS = "asset_register/sensors.xlsx"
HISTORIAN = "historian/readings.parquet"
MES_STATES = "mes/states.parquet"
MES_COUNTS = "mes/counts.parquet"
MES_REASONS = "mes/reason_codes.xlsx"
MES_CALENDAR = "mes/shift_calendar.xlsx"
ERP_PRODUCTS = "erp/products.xlsx"
ERP_ORDERS = "erp/production_orders.xlsx"
ERP_ROUTINGS_PREFIX = "erp/routings_"
CMMS_ORDERS = "cmms/work_orders.xlsx"

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    REGISTER_ASSETS: ("ASSET_NO", "SITE", "LINE", "EQUIPMENT_TYPE", "CRITICALITY", "WORKCENTER", "NAMEPLATE_CYCLE_S"),
    REGISTER_SENSORS: ("TAG", "ASSET_NO", "MEASUREMENT", "ENG_UNIT"),
    HISTORIAN: ("TAG", "TIMESTAMP_UTC", "VALUE", "QUALITY"),
    MES_STATES: ("WORKCENTER", "SEQ", "START_LOCAL", "END_LOCAL", "STATE", "REASON"),
    MES_COUNTS: ("WORKCENTER", "SHIFT_END_LOCAL", "ORDER_NO", "CUM_TOTAL", "CUM_SCRAP", "CUM_STARTUP_SCRAP"),
    MES_CALENDAR: ("SITE", "SHIFT_DATE", "SHIFT", "START_LOCAL", "END_LOCAL", "BREAK_MINUTES"),
    ERP_PRODUCTS: ("PRODUCT", "FAMILY"),
    ERP_ORDERS: ("ORDER_NO", "LINE", "PRODUCT", "QTY", "START_LOCAL", "END_LOCAL"),
    CMMS_ORDERS: ("WO_NO", "ASSET_NO", "TYPE", "FAILURE_CODE", "DESCRIPTION", "CREATED", "STARTED", "COMPLETED",
                  "DUE_DATE", "LABOUR_HOURS"),
}
ROUTING_RATE_COLUMNS = ("PARTS_PER_HOUR", "CYCLE_SECONDS")

Sources = Mapping[str, pd.DataFrame]


def routing_files(sources: Sources) -> list[str]:
    return sorted(path for path in sources if path.startswith(ERP_ROUTINGS_PREFIX))


def check_sources(sources: Sources) -> None:
    """Fail with every missing file and column listed, or return silently when the layout is complete."""
    problems = []
    for path, columns in REQUIRED_COLUMNS.items():
        if path not in sources:
            problems.append(f"missing file {path}")
            continue
        missing = [c for c in columns if c not in sources[path].columns]
        if missing:
            problems.append(f"{path} lacks columns {missing}")
    if not routing_files(sources):
        problems.append(f"no {ERP_ROUTINGS_PREFIX}<site>.xlsx files")
    for path in routing_files(sources):
        if not any(c in sources[path].columns for c in ROUTING_RATE_COLUMNS):
            problems.append(f"{path} has neither of {list(ROUTING_RATE_COLUMNS)}")
    if problems:
        raise ConformError("Source layout problems: " + "; ".join(problems))
