"""Reading saved consistency demo runs from a directory.

Runs are keyed by the model named inside each file, and a missing directory means no runs.
Files are written to a temporary directory; no real data is touched. The checked-in team recipes load against the catalog.
"""
from __future__ import annotations

import json
from pathlib import Path

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.services.service_factory import (
    RECIPES_FILE,
    load_saved_demo_runs,
    load_team_recipes,
)


def test_saved_runs_are_keyed_by_model(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps({"model": "org/model-a", "as_of": "2026-09-27"}), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"as_of": "2026-09-27"}), encoding="utf-8")
    runs = load_saved_demo_runs(tmp_path)
    assert set(runs) == {"org/model-a", "b"}


def test_missing_directory_means_no_runs(tmp_path: Path) -> None:
    assert load_saved_demo_runs(tmp_path / "absent") == {}


def test_team_recipes_load_against_the_catalog(catalog: SemanticCatalog) -> None:
    recipes = load_team_recipes(catalog, Path(__file__).resolve().parents[3] / RECIPES_FILE)
    assert {r.persona for r in recipes} == set(catalog.vocabulary.personas)
