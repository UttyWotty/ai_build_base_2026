"""Parsing of the illustrative team recipes: the checked-in file, and every way a recipe document can be wrong.

Recipes must name a known persona, an existing declared metric (or none), and exactly one read-only statement.
The checked-in file must parse against the real catalog.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from supply_ontology.core.team_recipes import RecipeParseError, parse_recipes
from supply_ontology.data_pipeline.semantic_files import load_yaml_document
from tests.supply_ontology.nl.conftest import CATALOG

RECIPES_FILE = Path(__file__).resolve().parents[3] / "demo" / "supply" / "team_recipes.yaml"
PERSONAS = CATALOG.vocabulary.personas
METRICS = CATALOG.metrics


def recipe(**overrides: object) -> dict[str, object]:
    fields = {"label": "Team report", "closest_metric": None, "choices": ["Uses the ship date."],
              "sql": "SELECT 0.5 AS answer FROM erp_sales_order_items"}
    return {"recipes": {"planning": {**fields, **overrides}}}


def test_checked_in_recipes_cover_every_persona() -> None:
    recipes = parse_recipes(load_yaml_document(RECIPES_FILE), PERSONAS, METRICS)
    assert [r.persona for r in recipes] == ["planning", "procurement", "logistics"]
    assert all(r.choices and r.sql.upper().startswith(("SELECT", "WITH")) for r in recipes)


@pytest.mark.parametrize("document, message", [
    ({}, "non-empty"),
    ({"recipes": {"finance": recipe()["recipes"]["planning"]}}, "unknown persona"),
    (recipe(closest_metric="otd_by_vibes"), "not a governed metric"),
    (recipe(choices=[]), "choices"),
    (recipe(sql="DELETE FROM erp_sales_order_items"), "Only SELECT"),
    (recipe(label=3), "must be text"),
])
def test_bad_recipe_documents_are_refused(document: object, message: str) -> None:
    with pytest.raises(RecipeParseError, match=message):
        parse_recipes(document, PERSONAS, METRICS)
