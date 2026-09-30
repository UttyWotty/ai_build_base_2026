"""Tests for the ontology and metric parsers.

They confirm that valid documents parse into the expected model and that shape errors name the offending path.
Explicit defaults (derived flag, time aggregation) are checked here too.
"""
from __future__ import annotations

import pytest

from supply_ontology.core.enums import Aggregation, Cardinality, TimeAggregation
from supply_ontology.core.errors import SemanticParseError
from supply_ontology.core.metric_parser import parse_metric
from supply_ontology.core.ontology_parser import parse_ontology
from tests.supply_ontology.core.semantic_fixtures import raw_metric, raw_ontology


def test_parses_valid_ontology() -> None:
    ontology = parse_ontology(raw_ontology())
    assert set(ontology.entities) == {"customer", "order", "order_line"}
    assert ontology.relationships[0].cardinality == Cardinality.MANY_TO_ONE
    assert ontology.relationships[0].join_columns == (("order_id", "order_id"),)
    assert ontology.hierarchies[0].levels == ("region", "country", "customer_id")


def test_attribute_derived_defaults_to_false() -> None:
    line = parse_ontology(raw_ontology()).entities["order_line"]
    assert line.attributes["qty"].derived is False
    assert line.attributes["is_on_time"].derived is True


def test_missing_required_field_names_path() -> None:
    document = raw_ontology()
    del document["entities"]["order"]["label"]
    with pytest.raises(SemanticParseError, match=r"ontology\.entities\.order\.label: is required"):
        parse_ontology(document)


def test_unknown_field_is_rejected() -> None:
    document = raw_ontology()
    document["entities"]["order"]["attributes"]["order_id"]["typ"] = "string"
    with pytest.raises(SemanticParseError, match="unknown field"):
        parse_ontology(document)


def test_bad_enum_value_lists_allowed_values() -> None:
    document = raw_ontology()
    document["entities"]["order_line"]["attributes"]["qty"]["type"] = "float"
    with pytest.raises(SemanticParseError, match="not one of: string, integer"):
        parse_ontology(document)


def test_empty_join_is_rejected() -> None:
    document = raw_ontology()
    document["relationships"][0]["join"] = {}
    with pytest.raises(SemanticParseError, match="at least one column pair"):
        parse_ontology(document)


def test_parses_valid_metric_with_defaults() -> None:
    metric = parse_metric(raw_metric(), "on_time.yaml")
    assert metric.numerator.aggregation == Aggregation.COUNT_IF
    assert metric.denominator is not None and metric.denominator.attribute is None
    assert metric.time_aggregation == TimeAggregation.ADDITIVE
    assert metric.filters[0].values == ("cancelled",)
    assert metric.not_to_be_confused_with == ()


def test_filter_list_value_becomes_tuple() -> None:
    document = raw_metric()
    document["filters"] = [{"attribute": "status", "operator": "in", "value": ["open", "closed"]}]
    assert parse_metric(document, "m.yaml").filters[0].values == ("open", "closed")


def test_boolean_parameter_is_rejected() -> None:
    document = raw_metric()
    document["parameters"] = {"window": True}
    with pytest.raises(SemanticParseError, match=r"parameters\.window: expected a number"):
        parse_metric(document, "m.yaml")


def test_metric_errors_are_prefixed_with_source() -> None:
    document = raw_metric()
    del document["grain"]
    with pytest.raises(SemanticParseError, match=r"m\.yaml\.grain: is required"):
        parse_metric(document, "m.yaml")
