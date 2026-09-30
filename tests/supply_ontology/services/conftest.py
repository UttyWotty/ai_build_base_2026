"""Fixtures for service tests: the real catalog and a DuckDB loaded with the conformed small world.

The small world is rendered and conformed in memory, exactly as the pipeline would do from files.
The database is shared across the session and treated as read-only.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.data_pipeline.conform.pipeline import conform_sources
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "supply"


@pytest.fixture(scope="session")
def catalog() -> SemanticCatalog:
    return load_catalog(SEMANTIC_DIR)


@pytest.fixture(scope="session")
def conformed_database(small_world: World, catalog: SemanticCatalog) -> DuckDBConnectionManager:
    window = int(catalog.metrics["days_of_inventory"].parameters["trailing_window_days"])
    tables = conform_sources({s.relative_path: s.frame for s in render_sources(small_world)}, catalog.ontology, window)
    manager = DuckDBConnectionManager()
    for name, frame in tables.items():
        manager.register_frame(name, frame)
    return manager
