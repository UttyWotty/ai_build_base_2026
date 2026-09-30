"""Fixtures for prediction tests: the conformed small plant in DuckDB and a prediction service with a compressed split.

The small plant covers 12 weeks, so the split fits one month, chooses thresholds on the next, and tests on the rest.
The service builds its panel once per session.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.prediction_settings import PredictionSettings
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.prediction_service import PredictionService
from tests.pdm_oee.conform.conftest import conformed, mappings, source_frames

__all__ = ["conformed", "mappings", "source_frames"]
SMALL_SETTINGS = PredictionSettings(fit_months=1, test_start_months=2)


@pytest.fixture(scope="session")
def small_database(conformed: dict) -> DuckDBConnectionManager:
    database = DuckDBConnectionManager()
    for name, frame in conformed.items():
        database.register_frame(name, frame)
    return database


@pytest.fixture(scope="session")
def prediction(catalog: PlantCatalog, small_database: DuckDBConnectionManager) -> PredictionService:
    return PredictionService(catalog, small_database, SMALL_SETTINGS)
