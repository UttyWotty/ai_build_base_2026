"""Filesystem adapter that reads every expected source export into a pandas frame.

Parquet files are read with pyarrow; xlsx files keep identifiers and codes as text and treat only empty cells as missing.
Missing files are reported by the layout check, so this reader only loads what exists.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pdm_oee.data_pipeline.conform.source_layout import (
    ERP_ROUTINGS_PREFIX,
    REQUIRED_COLUMNS,
)

PARQUET_SUFFIX = ".parquet"
XLSX_PATTERN = "*.xlsx"
TEXT_COLUMNS = {"ASSET_NO": "str", "WO_NO": "str", "FAILURE_CODE": "str", "WORKCENTER": "str", "TAG": "str",
                "ORDER_NO": "str", "PRODUCT": "str", "TYPE": "str", "SITE": "str", "SHIFT": "str"}
MISSING_MARKERS = [""]


def read_sources(sources_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every expected source file present under `sources_dir`, keyed by relative path."""
    routing_dir = (sources_dir / ERP_ROUTINGS_PREFIX).parent
    paths = [*REQUIRED_COLUMNS, *(str(p.relative_to(sources_dir)) for p in sorted(routing_dir.glob(XLSX_PATTERN))
                                  if p.name.startswith(Path(ERP_ROUTINGS_PREFIX).name))]
    frames = {}
    for relative in paths:
        path = sources_dir / relative
        if not path.exists():
            continue
        if path.suffix == PARQUET_SUFFIX:
            frames[relative] = pd.read_parquet(path, engine="pyarrow")
        else:
            frames[relative] = pd.read_excel(path, engine="openpyxl", dtype=TEXT_COLUMNS,
                                             keep_default_na=False, na_values=MISSING_MARKERS)
    return frames
