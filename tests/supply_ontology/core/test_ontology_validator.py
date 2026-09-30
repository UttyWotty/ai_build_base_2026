"""Tests for ontology consistency checks and join-path resolution.

Each test breaks one rule in an otherwise valid fixture and expects exactly that issue.
Join-path tests cover unique resolution, missing paths, and ambiguous diamonds.
"""
from __future__ import annotations

import pytest

from supply_ontology.core.errors import JoinPathError
from supply_ontology.core.join_paths import resolve_join_path
from supply_ontology.core.ontology_parser import parse_ontology
from supply_ontology.core.ontology_validator import validate_ontology
from tests.supply_ontology.core.semantic_fixtures import RawDocument, raw_ontology


def _messages(document: RawDocument) -> list[str]:
    return [str(issue) for issue in validate_ontology(parse_ontology(document))]


def _add_diamond(document: RawDocument) -> None:
    """Give order_line a second route to customer, bypassing order."""
    document["entities"]["order_line"]["attributes"]["customer_id"] = {"type": "string", "description": "Buyer."}
    document["relationships"].append(
        {"name": "line_customer", "from": "order_line", "to": "customer",
         "cardinality": "many_to_one", "join": {"customer_id": "customer_id"}}
    )


def test_valid_ontology_has_no_issues() -> None:
    assert _messages(raw_ontology()) == []


def test_key_column_must_be_an_attribute() -> None:
    document = raw_ontology()
    document["entities"]["order"]["key"] = ["order_number"]
    assert "entity order: key column 'order_number' is not an attribute" in _messages(document)


def test_names_must_be_snake_case() -> None:
    document = raw_ontology()
    document["entities"]["order"]["attributes"]["OrderDate"] = {"type": "date", "description": "D."}
    assert any("'OrderDate' must be lowercase snake_case" in m for m in _messages(document))


def test_relationship_to_unknown_entity() -> None:
    document = raw_ontology()
    document["relationships"][1]["to"] = "client"
    assert _messages(document) == ["relationship order_customer: entity 'client' is not declared"]


def test_join_type_mismatch() -> None:
    document = raw_ontology()
    document["entities"]["order"]["attributes"]["customer_id"]["type"] = "integer"
    assert any("type mismatch" in m for m in _messages(document))


def test_join_must_use_full_parent_key() -> None:
    document = raw_ontology()
    document["relationships"][1]["join"] = {"customer_id": "region"}
    assert any("must join on the full key of 'customer'" in m for m in _messages(document))


def test_duplicate_relationship_names() -> None:
    document = raw_ontology()
    document["relationships"][1]["name"] = "line_order"
    assert "relationship line_order: relationship name is declared 2 times" in _messages(document)


def test_hierarchy_level_must_exist_and_have_two_levels() -> None:
    document = raw_ontology()
    document["hierarchies"][0]["levels"] = ["continent"]
    messages = _messages(document)
    assert "hierarchy geography: level 'continent' is not an attribute of 'customer'" in messages
    assert "hierarchy geography: needs at least 2 levels" in messages


def test_ambiguous_join_path_is_an_issue() -> None:
    document = raw_ontology()
    _add_diamond(document)
    messages = _messages(document)
    assert len(messages) == 1
    assert "reaches 'customer' by more than one path" in messages[0]


def test_resolve_unique_path() -> None:
    ontology = parse_ontology(raw_ontology())
    path = resolve_join_path(ontology, "order_line", "customer")
    assert [r.name for r in path] == ["line_order", "order_customer"]
    assert resolve_join_path(ontology, "order", "order") == ()


def test_resolve_rejects_reverse_direction() -> None:
    with pytest.raises(JoinPathError, match="No declared relationship path"):
        resolve_join_path(parse_ontology(raw_ontology()), "customer", "order_line")


def test_resolve_rejects_ambiguous_path() -> None:
    document = raw_ontology()
    _add_diamond(document)
    with pytest.raises(JoinPathError, match="Ambiguous paths"):
        resolve_join_path(parse_ontology(document), "order_line", "customer")
