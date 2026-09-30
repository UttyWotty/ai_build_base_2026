"""Illustrative team recipes for the consistency demo: each team's own SQL for "customer on-time delivery" on the raw sources.

A recipe names its persona, the choices that differ from the governed definition, and the declared metric it effectively computes.
Parsing checks shape, known personas and metrics, and that every recipe is one read-only statement.
"""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from supply_ontology.core.errors import SemanticLayerError
from supply_ontology.core.naive_sql import NaiveSqlError, extract_select

RECIPES_KEY = "recipes"


class RecipeParseError(SemanticLayerError):
    """The team recipe file does not have the expected shape or refers to unknown names."""


@dataclass(frozen=True)
class TeamRecipe:
    """One team's way of computing the shared question, with what makes it different."""

    persona: str
    label: str
    choices: tuple[str, ...]
    closest_metric: str | None
    sql: str


def parse_recipes(raw: object, personas: Collection[str], metrics: Collection[str]) -> tuple[TeamRecipe, ...]:
    """Validate the recipe document and return the recipes in file order."""
    body = raw.get(RECIPES_KEY) if isinstance(raw, dict) else None
    if not isinstance(body, dict) or not body:
        raise RecipeParseError(f"Expected a non-empty '{RECIPES_KEY}' mapping.")
    return tuple(_parse_recipe(persona, fields, personas, metrics) for persona, fields in body.items())


def _parse_recipe(persona: object, fields: object, personas: Collection[str], metrics: Collection[str]) -> TeamRecipe:
    where = f"{RECIPES_KEY}.{persona}"
    if persona not in personas:
        raise RecipeParseError(f"{where}: unknown persona; expected one of {sorted(personas)}")
    if not isinstance(fields, dict):
        raise RecipeParseError(f"{where}: expected a mapping")
    label, choices, closest, sql = fields.get("label"), fields.get("choices"), fields.get("closest_metric"), fields.get("sql")
    if not isinstance(label, str) or not isinstance(sql, str):
        raise RecipeParseError(f"{where}: 'label' and 'sql' must be text")
    if not isinstance(choices, list) or not choices or not all(isinstance(c, str) for c in choices):
        raise RecipeParseError(f"{where}: 'choices' must be a non-empty list of text")
    if closest is not None and closest not in metrics:
        raise RecipeParseError(f"{where}: 'closest_metric' {closest!r} is not a governed metric")
    try:
        statement = extract_select(sql)
    except NaiveSqlError as error:
        raise RecipeParseError(f"{where}: {error}") from error
    return TeamRecipe(str(persona), label, tuple(choices), closest, statement)
