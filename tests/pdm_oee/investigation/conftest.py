"""Fixtures for investigation tests: a toolbox over the conformed small plant, with no saved alerts.

The OEE service is built once per session from the conform fixtures.
Each test builds its own service with its own scripted model.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.investigation_tools import ToolBox
from pdm_oee.services.oee_service import OEEService
from tests.pdm_oee.conform.conftest import conformed, mappings, source_frames

__all__ = ["conformed", "mappings", "source_frames"]


@pytest.fixture(scope="session")
def toolbox(conformed: dict, catalog: PlantCatalog) -> ToolBox:
    database = DuckDBConnectionManager()
    for name, frame in conformed.items():
        database.register_frame(name, frame)
    return ToolBox(catalog, OEEService(catalog, database), [])
