"""Contract between the generator and the governed ontology, plus the on-disk output of the writer.

Truth tables must carry exactly the non-derived attributes of their entity, unique keys, and resolvable foreign keys.
Writing the same world twice must produce byte-identical Parquet files and identical manifests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World
from supply_ontology.data_pipeline.synthetic.writer import (
    MANIFEST_FILENAME,
    write_dataset,
)
from tests.supply_ontology.conftest import SMALL_CONFIG

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "supply"


@pytest.fixture(scope="module")
def catalog() -> SemanticCatalog:
    return load_catalog(SEMANTIC_DIR)


def test_truth_tables_match_ontology_attributes(small_world: World, catalog: SemanticCatalog) -> None:
    assert set(small_world.tables) == set(catalog.ontology.entities)
    for name, entity in catalog.ontology.entities.items():
        expected = [a.name for a in entity.attributes.values() if not a.derived]
        assert list(small_world.tables[name].columns) == expected, name


def test_truth_keys_are_unique(small_world: World, catalog: SemanticCatalog) -> None:
    for name, entity in catalog.ontology.entities.items():
        assert not small_world.tables[name].duplicated(subset=list(entity.key)).any(), name


def test_every_relationship_resolves(small_world: World, catalog: SemanticCatalog) -> None:
    for relationship in catalog.ontology.relationships:
        child = small_world.tables[relationship.from_entity]
        parent = small_world.tables[relationship.to_entity]
        child_columns = [c for c, _ in relationship.join_columns]
        parent_columns = [p for _, p in relationship.join_columns]
        keys = set(map(tuple, parent[parent_columns].to_numpy()))
        missing = [row for row in map(tuple, child[child_columns].dropna().to_numpy()) if row not in keys]
        assert not missing, f"{relationship.name}: {missing[:3]}"


def test_writer_is_byte_deterministic(small_world: World, tmp_path: Path) -> None:
    sources = render_sources(small_world)
    first = write_dataset(small_world, sources, SMALL_CONFIG, tmp_path / "a")
    second = write_dataset(small_world, sources, SMALL_CONFIG, tmp_path / "b")
    assert first.read_bytes() == second.read_bytes()
    manifest = json.loads(first.read_text(encoding="utf-8"))
    assert manifest["story_facts"]["degrading_supplier_id"] == small_world.story_facts.degrading_supplier_id
    parquet = [p for p in manifest["files"] if p.endswith(".parquet")]
    assert parquet and all((tmp_path / "a" / p).read_bytes() == (tmp_path / "b" / p).read_bytes() for p in parquet)
    assert (tmp_path / "a" / MANIFEST_FILENAME).exists()
