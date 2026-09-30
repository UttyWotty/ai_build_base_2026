"""Decoding of ERP single-letter status codes into canonical status values.

The ERP uses A (open), C (closed), and X (cancelled) on purchase and sales documents.
Unknown codes raise ConformError rather than becoming nulls.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform.keys import map_or_fail

ERP_STATUS = pd.Series({"A": "open", "C": "closed", "X": "cancelled"})


def decode_status(codes: pd.Series, what: str) -> pd.Series:
    """Map ERP status codes to canonical values."""
    return map_or_fail(codes, ERP_STATUS, f"{what} status code")
