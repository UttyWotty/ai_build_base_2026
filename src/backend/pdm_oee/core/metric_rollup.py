"""Rolls governed metrics up to any grouping: sum the numerator measure, sum the denominator measure, then divide.

Ratios are never averaged. A group whose denominator is zero has no value (NaN), not zero or infinity.
Any measure frame with the measure ids as columns works, at any grain the metric's measures share.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from pdm_oee.core.catalog import PlantCatalog


def rollup(frame: pd.DataFrame, catalog: PlantCatalog, metric_ids: Sequence[str], group_by: Sequence[str]) -> pd.DataFrame:
    """One row per group, one column per metric."""
    columns = sorted({m for metric_id in metric_ids for m in (catalog.metrics[metric_id].numerator, catalog.metrics[metric_id].denominator)})
    sums = frame.groupby(list(group_by), sort=True)[columns].sum() if group_by else frame[columns].sum().to_frame().T
    result = pd.DataFrame(index=sums.index)
    for metric_id in metric_ids:
        metric = catalog.metrics[metric_id]
        denominator = sums[metric.denominator].astype(float)
        result[metric_id] = np.where(denominator > 0, sums[metric.numerator] / denominator.where(denominator > 0, 1.0), np.nan)
    return result.reset_index() if group_by else result.reset_index(drop=True)
