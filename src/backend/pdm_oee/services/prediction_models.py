"""The two predictors: the interpretable health-index baseline and a gradient-boosted classifier.

The baseline score is the worst normalised symptom over the last day; the classifier learns from every feature,
with the failure mode as a categorical input. Both produce one score per panel row, higher meaning more at risk.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from pdm_oee.core.feature_panel import STATS

BASELINE_STAT = STATS[0]
LEARNING_RATE = 0.05
MAX_ITERATIONS = 300
MAX_LEAF_NODES = 15
L2_REGULARISATION = 1.0
RANDOM_STATE = 0
POSITIVE_CLASS = 1


def health_index(panel: pd.DataFrame) -> np.ndarray:
    """The largest normalised short-window mean over the mode's symptoms; minus infinity when none is known."""
    columns = [c for c in panel.columns if c.startswith("s") and c.endswith(f"_{BASELINE_STAT}")]
    values = panel[columns].to_numpy(dtype=float)
    known = np.isfinite(values).any(axis=1)
    return np.where(known, np.nanmax(np.where(np.isfinite(values), values, -np.inf), axis=1), -np.inf)


def fit_classifier(panel: pd.DataFrame, rows: np.ndarray, features: list[str]) -> HistGradientBoostingClassifier:
    """Fit on the given eligible rows; the failure mode (first feature) is categorical."""
    model = HistGradientBoostingClassifier(learning_rate=LEARNING_RATE, max_iter=MAX_ITERATIONS, max_leaf_nodes=MAX_LEAF_NODES,
                                           l2_regularization=L2_REGULARISATION, categorical_features=[0],
                                           class_weight="balanced", random_state=RANDOM_STATE)
    model.fit(panel.loc[rows, features].to_numpy(dtype=float), panel.loc[rows, "label"].to_numpy(dtype=int))
    return model


def classifier_scores(model: HistGradientBoostingClassifier, panel: pd.DataFrame, features: list[str]) -> np.ndarray:
    return model.predict_proba(panel[features].to_numpy(dtype=float))[:, POSITIVE_CLASS]
