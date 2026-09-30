"""Failure prediction backtest over the conformed layer: build the hourly panel, fit, choose thresholds, and test.

Time is split into three consecutive blocks from the first hour of data: the classifier is fitted on the first, both
predictors' thresholds are chosen on the second within the false-alert budget, and both are scored once on the third.
The fitted classifier and its threshold are what the alert service (milestone 6) replays.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from pdm_oee.core.alert_scoring import (
    Evaluation,
    choose_threshold,
    evaluate,
    scoring_context,
)
from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import WorkType
from pdm_oee.core.feature_panel import build_panel, feature_names, sensor_features
from pdm_oee.core.prediction_settings import DEFAULT_SETTINGS, PredictionSettings
from pdm_oee.core.sensor_hours import epoch_starts, hourly_values, running_readings
from pdm_oee.data_pipeline.conform.pipeline import ENTITIES
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.prediction_models import (
    classifier_scores,
    fit_classifier,
    health_index,
)
from pdm_oee.services.settings import CONFORMED_DIR

TABLE_SQL = "SELECT * FROM {table}"
CANDIDATE_QUANTILES = np.linspace(0.90, 0.99999, 400)


@dataclass(frozen=True)
class Backtest:
    """Everything the backtest produced, for reporting and for replaying alerts."""

    panel: pd.DataFrame
    blocks: dict[str, np.ndarray]
    model: HistGradientBoostingClassifier
    features: list[str]
    scores: dict[str, np.ndarray]
    validation: dict[str, Evaluation]
    test: dict[str, Evaluation]


class PredictionService:
    """Builds the panel once and runs the backtest."""

    def __init__(self, catalog: PlantCatalog, connection_manager: DuckDBConnectionManager | None = None,
                 settings: PredictionSettings = DEFAULT_SETTINGS) -> None:
        self.catalog, self.settings = catalog, settings
        self.connection_manager = connection_manager or DuckDBConnectionManager(CONFORMED_DIR, list(ENTITIES))
        load = lambda name: self.connection_manager.execute(TABLE_SQL.format(table=name))  # noqa: E731
        self.tables = {name: load(name) for name in ("sensor_reading", "sensor", "asset", "machine_state", "failure_event", "work_order")}
        self.panel = self._panel()

    def _panel(self) -> pd.DataFrame:
        t = self.tables
        hours = pd.date_range(t["sensor_reading"]["ts"].min().floor("h"), t["sensor_reading"]["ts"].max().floor("h"), freq="h")
        instrument = t["work_order"][t["work_order"]["work_type"] == WorkType.INSTRUMENT.value]
        running = running_readings(t["sensor_reading"], t["sensor"], t["machine_state"])
        epochs = epoch_starts(t["sensor"], t["failure_event"], instrument, hours[0])
        hourly = hourly_values(running, t["sensor"], t["asset"], epochs, hours, self.catalog, self.settings)
        return build_panel(sensor_features(hourly, self.settings), t["asset"], t["failure_event"], self.catalog, self.settings)

    def blocks(self) -> dict[str, np.ndarray]:
        """Fit, validation, and test rows by hour."""
        first = self.panel["hour"].min().normalize()
        fit_end = first + pd.DateOffset(months=self.settings.fit_months)
        test_start = first + pd.DateOffset(months=self.settings.test_start_months)
        hour = self.panel["hour"]
        return {"fit": (hour < fit_end).to_numpy(), "validation": ((hour >= fit_end) & (hour < test_start)).to_numpy(),
                "test": (hour >= test_start).to_numpy()}

    def backtest(self) -> Backtest:
        blocks, features = self.blocks(), feature_names(self.catalog)
        eligible = self.panel["eligible"].to_numpy()
        model = fit_classifier(self.panel, blocks["fit"] & eligible, features)
        scores = {"model": classifier_scores(model, self.panel, features), "baseline": health_index(self.panel)}
        assets, context = self.panel["asset_id"].nunique(), scoring_context(self.panel)
        validation, test = {}, {}
        for name, score in scores.items():
            finite = score[blocks["validation"] & eligible & np.isfinite(score)]
            chosen = choose_threshold(context, score, blocks["validation"], self.settings, assets, np.quantile(finite, CANDIDATE_QUANTILES))
            validation[name] = chosen
            test[name] = evaluate(context, score, chosen.threshold, blocks["test"], self.settings, assets)
        return Backtest(self.panel, blocks, model, features, scores, validation, test)
