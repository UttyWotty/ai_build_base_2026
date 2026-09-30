"""Tests for metric consistency checks and catalog construction.

Each test breaks one metric rule against the fixture ontology and expects that specific issue.
Catalog tests confirm that every issue is collected before the build fails.
"""
from __future__ import annotations

import pytest

from supply_ontology.core.catalog import build_catalog
from supply_ontology.core.errors import CatalogValidationError
from supply_ontology.core.metric_parser import parse_metric
from supply_ontology.core.metric_validator import validate_metrics
from supply_ontology.core.ontology_parser import parse_ontology
from supply_ontology.core.terms import normalize_term
from supply_ontology.core.vocabulary_model import EMPTY_VOCABULARY
from tests.supply_ontology.core.semantic_fixtures import (
    RawDocument,
    raw_metric,
    raw_ontology,
)


def _messages(*documents: RawDocument) -> list[str]:
    metrics = [parse_metric(d, f"{d['id']}.yaml") for d in documents]
    return [issue.message for issue in validate_metrics(metrics, parse_ontology(raw_ontology()))]


def test_valid_metric_has_no_issues() -> None:
    assert _messages(raw_metric()) == []


def test_unknown_grain_stops_further_checks() -> None:
    document = raw_metric()
    document["grain"] = "invoice"
    assert _messages(document) == ["grain entity 'invoice' is not declared"]


def test_time_dimension_must_be_a_date() -> None:
    document = raw_metric()
    document["time_dimension"] = "status"
    assert _messages(document) == ["time_dimension 'status' must be a date attribute of 'order_line'"]


def test_sum_requires_numeric_attribute() -> None:
    document = raw_metric()
    document["numerator"] = {"aggregation": "sum", "attribute": "status"}
    assert _messages(document) == ["sum needs a numeric attribute; 'status' is string"]


def test_count_if_requires_boolean_attribute() -> None:
    document = raw_metric()
    document["numerator"] = {"aggregation": "count_if", "attribute": "qty"}
    assert _messages(document) == ["count_if needs a boolean attribute; 'qty' is integer"]


def test_count_takes_no_attribute() -> None:
    document = raw_metric()
    document["denominator"] = {"aggregation": "count", "attribute": "qty"}
    assert _messages(document) == ["count counts grain rows and takes no attribute"]


def test_ratio_and_simple_shapes() -> None:
    ratio = raw_metric("ratio_metric")
    del ratio["denominator"]
    simple = raw_metric("simple_metric")
    simple["type"] = "simple"
    assert _messages(ratio, simple) == [
        "ratio metric requires a denominator",
        "simple metric must not declare a denominator",
    ]


def test_filter_value_count_and_type() -> None:
    document = raw_metric()
    document["filters"] = [
        {"attribute": "status", "operator": "equals", "value": ["open", "closed"]},
        {"attribute": "qty", "operator": "in", "value": ["ten"]},
        {"attribute": "due_date", "operator": "equals", "value": "2026-02-30"},
    ]
    assert _messages(document) == [
        "equals takes exactly one value",
        "value 'ten' does not match type integer",
        "value '2026-02-30' does not match type date",
    ]


def test_boolean_is_not_accepted_as_integer() -> None:
    document = raw_metric()
    document["filters"] = [{"attribute": "qty", "operator": "equals", "value": True}]
    assert _messages(document) == ["value True does not match type integer"]


def test_duplicate_metric_ids() -> None:
    assert "id is declared 2 times" in _messages(raw_metric("same"), raw_metric("same"))


def test_confusion_references_must_exist_and_not_be_self() -> None:
    document = raw_metric("alpha")
    document["not_to_be_confused_with"] = ["alpha", "beta"]
    assert _messages(document) == [
        "lists itself in not_to_be_confused_with",
        "not_to_be_confused_with names unknown metric 'beta'",
    ]


def test_synonym_may_not_resolve_to_two_metrics() -> None:
    first = raw_metric("alpha")
    second = raw_metric("beta")
    second["synonyms"] = ["Synonym-ALPHA"]
    assert _messages(first, second) == ["term 'synonym alpha' already resolves to metric 'alpha'"]


def test_normalize_term_collapses_case_and_separators() -> None:
    assert normalize_term("  On-Time_Delivery  ") == "on time delivery"


def test_build_catalog_collects_all_issues() -> None:
    ontology_document = raw_ontology()
    ontology_document["entities"]["order"]["key"] = ["missing"]
    metric_document = raw_metric()
    metric_document["grain"] = "invoice"
    with pytest.raises(CatalogValidationError) as raised:
        build_catalog(parse_ontology(ontology_document), [parse_metric(metric_document, "m.yaml")], EMPTY_VOCABULARY)
    assert len(raised.value.issues) >= 2


def test_build_catalog_indexes_metrics_by_id() -> None:
    catalog = build_catalog(parse_ontology(raw_ontology()), [parse_metric(raw_metric(), "m.yaml")], EMPTY_VOCABULARY)
    assert catalog.metric("on_time") is not None
    assert catalog.metric("missing") is None
