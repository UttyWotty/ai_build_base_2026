"""Compares a conformed table with its truth table: same columns, same rows by key, same values.

Rows are aligned by the entity's key columns; missing values compare equal whatever their dtype (None, NaN, NaT);
floats may differ by at most FLOAT_TOLERANCE, which covers rounding after unit conversion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FLOAT_TOLERANCE = 0.002


def differences(conformed: pd.DataFrame, truth: pd.DataFrame, keys: tuple[str, ...]) -> list[str]:
    """Human-readable differences; empty when the tables match."""
    if set(conformed.columns) != set(truth.columns):
        return [f"columns differ: {sorted(set(conformed.columns) ^ set(truth.columns))}"]
    if len(conformed) != len(truth):
        return [f"row counts differ: {len(conformed)} vs {len(truth)}"]
    left = conformed.sort_values(list(keys)).reset_index(drop=True)
    right = truth[list(conformed.columns)].sort_values(list(keys)).reset_index(drop=True)
    return [problem for column in conformed.columns if (problem := _column_problem(column, left[column], right[column]))]


def _column_problem(column: str, left: pd.Series, right: pd.Series) -> str | None:
    missing = left.isna().to_numpy() & right.isna().to_numpy()
    if pd.api.types.is_float_dtype(right) and pd.api.types.is_numeric_dtype(left):
        close = np.isclose(left.to_numpy(dtype=float), right.to_numpy(dtype=float), atol=FLOAT_TOLERANCE) | missing
    elif pd.api.types.is_datetime64_any_dtype(right):
        close = (pd.to_datetime(left).to_numpy() == pd.to_datetime(right).to_numpy()) | missing
    else:
        close = (left.astype(object).to_numpy() == right.astype(object).to_numpy()) | missing
    if close.all():
        return None
    first = int(np.flatnonzero(~close)[0])
    return f"{column}: {int((~close).sum())} rows differ, first {left.iloc[first]!r} vs {right.iloc[first]!r}"
