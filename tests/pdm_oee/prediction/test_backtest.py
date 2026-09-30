"""The backtest on the small plant runs end to end, keeps its blocks apart, and the model store round-trips.

Numbers on 12 weeks are not meaningful; the tests check structure: disjoint blocks, both predictors evaluated with
thresholds from the validation block, scores for every row, and a saved model that scores identically when loaded.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from pdm_oee.data_pipeline.model_store import load_model, save_model
from pdm_oee.services.prediction_models import classifier_scores
from pdm_oee.services.prediction_service import PredictionService


def test_backtest_structure_and_model_store(prediction: PredictionService, tmp_path: Path) -> None:
    backtest = prediction.backtest()
    blocks = backtest.blocks
    assert blocks["fit"].any() and blocks["validation"].any() and blocks["test"].any()
    assert not (blocks["fit"] & blocks["validation"]).any() and not (blocks["validation"] & blocks["test"]).any()
    assert set(backtest.test) == {"model", "baseline"}
    for name in ("model", "baseline"):
        assert backtest.test[name].threshold == backtest.validation[name].threshold
        assert len(backtest.scores[name]) == len(backtest.panel)
    save_model(backtest.model, {"threshold": backtest.validation["model"].threshold}, tmp_path)
    model, report = load_model(tmp_path)
    assert report["threshold"] == backtest.validation["model"].threshold
    assert np.allclose(classifier_scores(model, backtest.panel, backtest.features), backtest.scores["model"])
