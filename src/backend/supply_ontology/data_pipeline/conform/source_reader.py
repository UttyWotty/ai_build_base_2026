"""Filesystem adapter that reads every expected source export into a pandas frame.

Parquet files are read with pyarrow; xlsx files with openpyxl, keeping identifier columns and codes such as "NA" as text.
Missing files are reported by the pipeline's layout check, so this reader only loads what exists.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from supply_ontology.data_pipeline.conform.source_layout import REQUIRED_COLUMNS

PARQUET_SUFFIX = ".parquet"
# xlsx columns that hold identifiers and must stay text even when they look numeric.
TEXT_COLUMNS: dict[str, str] = {"PO Number": "str", "PARTNER_CODE": "str", "ERP_NUMBER": "str"}
# Only empty cells are missing. pandas' defaults would also turn text such as "NA" (the North America region) into NaN.
MISSING_MARKERS = [""]


def read_sources(sources_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every expected source file present under `sources_dir`, keyed by relative path."""
    frames = {}
    for relative in REQUIRED_COLUMNS:
        path = sources_dir / relative
        if not path.exists():
            continue
        if path.suffix == PARQUET_SUFFIX:
            frames[relative] = pd.read_parquet(path, engine="pyarrow")
        else:
            frames[relative] = pd.read_excel(
                path, engine="openpyxl", dtype=TEXT_COLUMNS, keep_default_na=False, na_values=MISSING_MARKERS
            )
    return frames
