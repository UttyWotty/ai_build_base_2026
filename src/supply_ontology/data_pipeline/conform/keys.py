"""Builders for canonical composite keys and lookups that fail loudly on unmapped values.

Composite ids join a document number and a zero-padded item number, matching the ERP-style canonical formats.
map_or_fail is used wherever a missing mapping would otherwise silently produce nulls.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform.errors import ConformError

KEY_SEPARATOR = "-"
PO_ITEM_WIDTH = 5
SO_ITEM_WIDTH = 3
SAMPLE_SIZE = 5


def composite_id(document: pd.Series, item: pd.Series, width: int) -> pd.Series:
    """Join a document number and an item number padded to `width` digits."""
    return document.astype(str) + KEY_SEPARATOR + item.astype(int).astype(str).str.zfill(width)


def map_or_fail(values: pd.Series, mapping: pd.Series, what: str) -> pd.Series:
    """Map values through a lookup Series; raise ConformError listing samples of unmapped values."""
    if mapping.index.has_duplicates:
        raise ConformError(f"{what}: lookup has duplicate keys {mapping.index[mapping.index.duplicated()][:SAMPLE_SIZE].tolist()}")
    mapped = values.map(mapping)
    unmapped = values[mapped.isna() & values.notna()]
    if not unmapped.empty:
        raise ConformError(f"{what}: {unmapped.nunique()} unmapped value(s), e.g. {unmapped.unique()[:SAMPLE_SIZE].tolist()}")
    return mapped
