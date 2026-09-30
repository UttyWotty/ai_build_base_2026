"""The checked-in catalog loads and validates, and the YAML loader refuses duplicate keys and missing metric files.

These tests read the real semantic/ directory, so a broken catalog file fails the suite.
Temporary directories are used for the error cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pdm_oee.core.enums import Factor
from pdm_oee.core.errors import SemanticFileError
from pdm_oee.data_pipeline.semantic_files import load_catalog, load_yaml_document

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "pdm"


def test_checked_in_catalog_is_valid_and_complete() -> None:
    catalog = load_catalog(SEMANTIC_DIR)
    assert set(catalog.plant.asset_classes) == {"cnc_machining_centre", "hydraulic_press", "conveyor_drive"}
    assert {loss.factor for loss in catalog.losses.losses.values()} == set(Factor)
    assert {"oee", "availability", "performance", "quality", "teep", "mtbf", "mttr"} <= set(catalog.metrics)
    assert catalog.measures["run_time"].parameters["small_stop_threshold_minutes"] == 5


def test_every_asset_class_has_a_predictable_and_the_plan_has_an_unpredictable_mode() -> None:
    catalog = load_catalog(SEMANTIC_DIR)
    modes = [m for c in catalog.plant.asset_classes.values() for m in c.failure_modes.values()]
    for asset_class in catalog.plant.asset_classes.values():
        assert any(m.predictable for m in asset_class.failure_modes.values()), asset_class.id
    assert [m.id for m in modes if not m.predictable] == ["tool_changer_jam"]


def test_duplicate_yaml_keys_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "plant.yaml"
    path.write_text("sensor_types: {}\nsensor_types: {}\n", encoding="utf-8")
    with pytest.raises(SemanticFileError, match="duplicate key"):
        load_yaml_document(path)


def test_missing_metric_files_are_reported(tmp_path: Path) -> None:
    (tmp_path / "metrics").mkdir()
    with pytest.raises(SemanticFileError, match="No metric files"):
        load_catalog(tmp_path)
