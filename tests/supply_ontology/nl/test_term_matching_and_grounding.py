"""Deterministic language rules: which metric the wording binds, and which grain, range, and dimensions it supports.

These rules are what make different phrasings of the same question produce the same spec.
Each case is a phrase a real user might type.
"""
from __future__ import annotations

from datetime import date

import pytest

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.enums import TimeGrain
from supply_ontology.core.grounding import (
    grounded_dimensions,
    grounded_time_range,
    requested_time_grain,
)
from supply_ontology.core.query_spec import DimensionRef, TimeRange
from supply_ontology.core.term_matcher import (
    build_context_index,
    build_term_index,
    match_terms,
)
from tests.supply_ontology.nl.conftest import CATALOG

AS_OF = date(2026, 9, 27)
ANCHORS = calendar_anchors(AS_OF)


def bound(question: str, persona: str | None = None) -> tuple[str, ...]:
    return match_terms(question, build_term_index(CATALOG, persona), build_context_index(CATALOG)).bound_metrics


@pytest.mark.parametrize(("question", "persona", "expected"), [
    ("What was OTD last quarter?", None, ("otd",)),
    ("supplier on-time delivery by vendor", None, ("supplier_otd",)),
    ("What was our service level?", "planning", ("otd",)),
    ("What was our service level?", "procurement", ()),
    ("line fill rate and fill rate", None, ("line_fill_rate", "fill_rate")),
    ("Were we on time for suppliers?", None, ("supplier_otd",)),
    ("share of customer orders that arrived on time", None, ("otd",)),
    ("how are we doing on time", None, ()),
    ("employee headcount", None, ()),
])
def test_wording_binds_metrics(question: str, persona: str | None, expected: tuple[str, ...]) -> None:
    assert bound(question, persona) == expected


def test_unsettled_ambiguity_lists_candidates() -> None:
    matches = match_terms("how are we doing on time", build_term_index(CATALOG, None), build_context_index(CATALOG))
    assert matches.ambiguous[0].metrics == ("otd", "supplier_otd", "carrier_on_time")


@pytest.mark.parametrize(("question", "grain"), [
    ("OTD last quarter", None), ("OTD by month", TimeGrain.MONTH), ("quarterly fill rate", TimeGrain.QUARTER),
    ("OTD trend", TimeGrain.MONTH), ("weekly carrier performance", TimeGrain.WEEK),
])
def test_time_grain_needs_trend_wording(question: str, grain: TimeGrain | None) -> None:
    assert requested_time_grain(question) == grain


def test_time_range_comes_from_anchor_wording() -> None:
    proposed = TimeRange(date(2020, 1, 1), date(2020, 3, 31))
    assert grounded_time_range("OTD for the previous quarter", proposed, ANCHORS) == TimeRange(date(2026, 4, 1), date(2026, 6, 30))
    assert grounded_time_range("OTD YTD", proposed, ANCHORS) == TimeRange(date(2026, 1, 1), AS_OF)
    assert grounded_time_range("OTD in Q1 2020", proposed, ANCHORS) == proposed
    assert grounded_time_range("current OTD", proposed, ANCHORS) is None


def test_calendar_anchors() -> None:
    assert ANCHORS["last month"] == TimeRange(date(2026, 8, 1), date(2026, 8, 31))
    assert ANCHORS["last year"] == TimeRange(date(2025, 1, 1), date(2025, 12, 31))
    assert ANCHORS["last 12 complete months"] == TimeRange(date(2025, 9, 1), date(2026, 8, 31))
    assert ANCHORS["this quarter to date"] == TimeRange(date(2026, 7, 1), AS_OF)


def names(question: str, proposed: tuple[DimensionRef, ...] = (), persona: str | None = None) -> list[str]:
    return [d.name for d in grounded_dimensions(question, proposed, CATALOG.vocabulary, persona)]


def test_dimensions_follow_the_wording() -> None:
    assert names("landed cost by part family") == ["part.family"]
    assert names("OTD by plant and customer segment") == ["plant.plant_id", "customer.segment"]
    assert names("fill rate per sku") == ["part.part_id"]
    assert names("OTD last quarter", (DimensionRef("part", "category"),)) == []
    assert names("OTD for bearings by site", (DimensionRef("part", "category"),)) == ["plant.plant_id"]
    assert names("DOI by stocking location", persona="planning") == ["plant.plant_id"]
