"""Integration tests for the YAML adapter and the checked-in semantic layer.

The first test loads the real semantic/ directory, so any broken governed definition fails the suite.
The remaining tests use temporary files to prove duplicate keys and missing metric files are rejected.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from supply_ontology.core.enums import TimeAggregation
from supply_ontology.core.errors import SemanticFileError
from supply_ontology.data_pipeline.semantic_files import (
    load_catalog,
    load_yaml_document,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_DIR = REPO_ROOT / "semantic" / "supply"
CANONICAL_METRICS = {"otd", "fill_rate", "days_of_inventory", "landed_cost_per_unit", "supplier_otd"}


def test_checked_in_semantic_layer_is_valid() -> None:
    catalog = load_catalog(SEMANTIC_DIR)
    assert CANONICAL_METRICS <= set(catalog.metrics)
    doi = catalog.metrics["days_of_inventory"]
    assert doi.time_aggregation == TimeAggregation.PERIOD_END
    assert doi.parameters["trailing_window_days"] == 90


def test_duplicate_yaml_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.yaml"
    path.write_text("id: a\nid: b\n", encoding="utf-8")
    with pytest.raises(SemanticFileError, match="duplicate key 'id'"):
        load_yaml_document(path)


def test_missing_metric_directory_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "ontology.yaml").write_text((SEMANTIC_DIR / "ontology.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(SemanticFileError, match="No metric files"):
        load_catalog(tmp_path)
