"""Fixtures for conform tests: the source mappings, the small plant's rendered sources, and their conformed tables.

Conforming runs once per session on the in-memory sources; tests that break a source copy the frames first.
The small plant and catalog fixtures come from tests/conftest.py.
"""
from __future__ import annotations

import pandas as pd
import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.pipeline import conform_sources
from pdm_oee.data_pipeline.semantic_files import load_source_mappings
from tests.pdm_oee.conftest import SEMANTIC_DIR


@pytest.fixture(scope="session")
def mappings(catalog: PlantCatalog) -> SourceMappings:
    return load_source_mappings(SEMANTIC_DIR, catalog)


@pytest.fixture(scope="session")
def source_frames(small_sources: dict) -> dict[str, pd.DataFrame]:
    return {path: source.frame for path, source in small_sources.items()}


@pytest.fixture(scope="session")
def conformed(source_frames: dict, catalog: PlantCatalog, mappings: SourceMappings) -> dict[str, pd.DataFrame]:
    return conform_sources(source_frames, catalog, mappings)
