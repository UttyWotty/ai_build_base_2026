"""End-to-end conform through real files: write sources, read them back, conform, and query through DuckDB views.

Reading xlsx from disk introduces traps that in-memory tests cannot see, such as the region code "NA" becoming NaN.
The DuckDB adapter must expose every entity as a view with the same row count as the conformed frame.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from supply_ontology.data_pipeline.conform.conformed_store import write_conformed
from supply_ontology.data_pipeline.conform.pipeline import conform_sources
from supply_ontology.data_pipeline.conform.source_reader import read_sources
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World
from supply_ontology.data_pipeline.synthetic.writer import (
    SOURCES_DIRNAME,
    write_dataset,
)
from tests.supply_ontology.conftest import SMALL_CONFIG

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "supply"


def test_file_roundtrip_reconstructs_truth_and_serves_views(small_world: World, tmp_path: Path) -> None:
    catalog = load_catalog(SEMANTIC_DIR)
    write_dataset(small_world, render_sources(small_world), SMALL_CONFIG, tmp_path)
    window = int(catalog.metrics["days_of_inventory"].parameters["trailing_window_days"])
    tables = conform_sources(read_sources(tmp_path / SOURCES_DIRNAME), catalog.ontology, window)
    for name, entity in catalog.ontology.entities.items():
        truth = small_world.tables[name].sort_values(list(entity.key)).reset_index(drop=True)
        actual = tables[name][list(truth.columns)].sort_values(list(entity.key)).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual, truth, check_dtype=False, rtol=1e-9, obj=name)
    write_conformed(tables, tmp_path / "conformed")
    manager = DuckDBConnectionManager(tmp_path / "conformed", list(catalog.ontology.entities))
    for name in catalog.ontology.entities:
        assert manager.execute(f"SELECT count(*) AS n FROM {name}")["n"].iloc[0] == len(tables[name])
    regions = manager.execute("SELECT DISTINCT region FROM plant ORDER BY region")["region"].tolist()
    assert "NA" in regions
    manager.close()
