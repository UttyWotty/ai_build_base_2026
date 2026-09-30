"""Every conformed table equals its truth table, in memory and after a real round trip through files.

The truth tables are never read by the pipeline; they are only the answer key here.
One test changes a single value to prove the comparison would notice.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.conformed_store import (
    read_conformed,
    write_conformed,
)
from pdm_oee.data_pipeline.conform.pipeline import ENTITY_KEYS, conform_sources
from pdm_oee.data_pipeline.conform.source_reader import read_sources
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.data_pipeline.synthetic.world import World
from pdm_oee.data_pipeline.synthetic.writer import write_dataset
from tests.pdm_oee.conform.table_comparison import differences
from tests.pdm_oee.conftest import SMALL_CONFIG


@pytest.mark.parametrize("entity", list(ENTITY_KEYS))
def test_conformed_table_equals_truth(entity: str, conformed: dict, small_world: World) -> None:
    assert differences(conformed[entity], small_world.tables[entity], ENTITY_KEYS[entity]) == []


def test_comparison_notices_a_changed_value(conformed: dict, small_world: World) -> None:
    changed = conformed["production_count"].copy()
    changed.loc[changed.index[0], "scrap_count"] += 1
    assert differences(changed, small_world.tables["production_count"], ENTITY_KEYS["production_count"])


def test_file_round_trip_and_duckdb_views(small_world: World, small_sources: dict, catalog: PlantCatalog,
                                          mappings: SourceMappings, tmp_path: Path) -> None:
    write_dataset(small_world, list(small_sources.values()), SMALL_CONFIG, tmp_path)
    tables = conform_sources(read_sources(tmp_path / "sources"), catalog, mappings)
    for entity, keys in ENTITY_KEYS.items():
        assert differences(tables[entity], small_world.tables[entity], keys) == [], entity
    write_conformed(tables, tmp_path / "conformed")
    assert set(read_conformed(tmp_path / "conformed", list(ENTITY_KEYS))) == set(ENTITY_KEYS)
    database = DuckDBConnectionManager(tmp_path / "conformed", list(ENTITY_KEYS))
    count = database.execute("SELECT count(*) AS n FROM failure_event WHERE asset_id = ?", ["US1-L2-01"])["n"].iloc[0]
    assert count == (small_world.tables["failure_event"]["asset_id"] == "US1-L2-01").sum()
