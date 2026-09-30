"""Fixtures for compiler tests: the catalog and an in-memory DuckDB loaded with the golden world.

The database is built once per module run and never written to by tests.
Frames come from golden_world.py so every expected value stays hand-derived.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.semantic_files import load_catalog
from tests.supply_ontology.compiler.golden_world import golden_frames

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "supply"
CATALOG: SemanticCatalog = load_catalog(SEMANTIC_DIR)


@pytest.fixture(scope="session")
def database() -> DuckDBConnectionManager:
    manager = DuckDBConnectionManager()
    for name, frame in golden_frames(CATALOG.ontology).items():
        manager.register_frame(name, frame)
    return manager
