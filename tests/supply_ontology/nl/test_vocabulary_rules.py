"""Vocabulary governance: every phrase must mean one thing, and personas can extend but never redefine.

Each test adds one bad entry to the real vocabulary and expects the matching issue.
The checked-in vocabulary itself must be clean.
"""
from __future__ import annotations

from dataclasses import replace

from supply_ontology.core.vocabulary_model import DimensionDefinition, Persona
from supply_ontology.core.vocabulary_validator import validate_vocabulary
from tests.supply_ontology.nl.conftest import CATALOG

METRICS = list(CATALOG.metrics.values())


def issues_with(**changes: object) -> list[str]:
    vocabulary = replace(CATALOG.vocabulary, **changes)
    return [issue.message for issue in validate_vocabulary(vocabulary, CATALOG.ontology, METRICS)]


def test_checked_in_vocabulary_is_clean() -> None:
    assert issues_with() == []


def test_dimension_synonym_may_not_be_a_metric_term() -> None:
    dimensions = {**CATALOG.vocabulary.dimensions, "part.uom": DimensionDefinition("part.uom", "unit", ("fill rate",))}
    assert "synonym 'fill rate' is a metric term" in issues_with(dimensions=dimensions)


def test_derived_attribute_cannot_be_a_dimension() -> None:
    dimensions = {**CATALOG.vocabulary.dimensions, "receipt.landed_cost_usd": DimensionDefinition("receipt.landed_cost_usd", "landed value", ())}
    assert "derived attributes cannot be dimensions" in issues_with(dimensions=dimensions)


def test_persona_cannot_redefine_a_governed_term() -> None:
    rogue = Persona("rogue", "Rogue", "Redefines things.", {"OTD": "supplier_otd"}, {}, ())
    assert "phrase 'OTD' would redefine governed term for 'otd'" in issues_with(personas={**CATALOG.vocabulary.personas, "rogue": rogue})


def test_ambiguous_terms_need_distinct_context_words() -> None:
    terms = {**CATALOG.vocabulary.ambiguous_terms, "delivery": {"otd": ("orders",), "supplier_otd": ("orders",)}}
    assert "context word 'orders' is shared by 'otd' and 'supplier_otd'" in issues_with(ambiguous_terms=terms)
