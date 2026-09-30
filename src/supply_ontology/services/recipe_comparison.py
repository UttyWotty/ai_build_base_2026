"""Runs each team's recipe on the raw sources and the governed metric for the same period, without a language model.

This is the deterministic half of the consistency demo: the disagreement it shows does not depend on how a model behaves on the day.
Failures of a recipe are recorded on its run, so one broken recipe never hides the others.
"""
from __future__ import annotations

from collections.abc import Sequence

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.demo_script import DEMO_PERIOD_ANCHOR, SHARED_METRIC
from supply_ontology.core.query_spec import QuerySpec, TimeRange
from supply_ontology.core.team_recipes import TeamRecipe
from supply_ontology.data_pipeline.raw_source_database import (
    RawQueryError,
    RawSourceDatabase,
)
from supply_ontology.services.demo_models import (
    RecipeComparison,
    RecipeRun,
    answer_value,
)
from supply_ontology.services.query_service import QueryService


def compare_recipes(
    recipes: Sequence[TeamRecipe], raw_database: RawSourceDatabase, query_service: QueryService,
) -> RecipeComparison:
    """Run every recipe and the governed shared metric over the demo period."""
    period = calendar_anchors(query_service.as_of)[DEMO_PERIOD_ANCHOR]
    runs = tuple(_run(recipe, raw_database, period) for recipe in recipes)
    governed = query_service.run(QuerySpec(metrics=(SHARED_METRIC,), dimensions=(), filters=(), time_range=period, time_grain=None))
    value = governed.frame[SHARED_METRIC].iloc[0] if len(governed.frame) == 1 else None
    return RecipeComparison(period, runs, SHARED_METRIC, None if value is None else float(value), governed.compiled.fingerprint)


def _run(recipe: TeamRecipe, raw_database: RawSourceDatabase, period: TimeRange) -> RecipeRun:
    try:
        frame = raw_database.run_select(recipe.sql, (period.start.isoformat(), period.end.isoformat()))
    except RawQueryError as error:
        return RecipeRun(recipe, None, str(error))
    return RecipeRun(recipe, answer_value(frame), None)
