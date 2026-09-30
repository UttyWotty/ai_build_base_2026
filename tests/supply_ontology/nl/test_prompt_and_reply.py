"""Prompt construction and model reply parsing.

The system message must be identical for every persona and question, so the model server can reuse its prompt cache.
Reply parsing must survive thinking blocks, code fences, and prose, and reject anything that is not a decision.
"""
from __future__ import annotations

from datetime import date

import pytest

from supply_ontology.core.model_response import (
    ClarifyDecision,
    ModelOutputError,
    QueryDecision,
    UnsupportedDecision,
    parse_decision,
)
from supply_ontology.core.prompt_builder import build_system_message, build_user_message
from supply_ontology.core.term_matcher import (
    build_context_index,
    build_term_index,
    match_terms,
)
from tests.supply_ontology.nl.conftest import CATALOG

VALUES = {"plant.plant_id": ["CN01", "DE01", "MX01", "US01"], "part.part_id": [f"P-{i:06d}" for i in range(300)]}


def test_system_message_lists_catalog_anchors_and_short_value_lists() -> None:
    content = build_system_message(CATALOG, date(2026, 9, 27), VALUES)["content"]
    assert "- otd: On-time delivery (customer)." in content
    assert '- last quarter: {"start": "2026-04-01", "end": "2026-06-30"}' in content
    assert "Values: CN01, DE01, MX01, US01." in content
    assert "P-000001" not in content


def test_user_message_carries_persona_and_binding() -> None:
    matches = match_terms("service level by site", build_term_index(CATALOG, "planning"), build_context_index(CATALOG))
    content = build_user_message("service level by site", "planning", CATALOG, matches)["content"]
    assert "Planning team" in content and "Metrics bound by wording (use exactly these): otd" in content


@pytest.mark.parametrize("reply", [
    '{"action": "query", "spec": {"metrics": ["otd"]}}',
    '<think>let me see {not json}</think>\n```json\n{"action": "query", "spec": {"metrics": ["otd"]}}\n```',
    'Sure! Here you go: {"action": "query", "spec": {"metrics": ["otd"]}} Hope that helps.',
])
def test_query_replies_parse(reply: str) -> None:
    assert parse_decision(reply) == QueryDecision(spec={"metrics": ["otd"]})


def test_clarify_and_unsupported_replies_parse() -> None:
    assert parse_decision('{"action": "clarify", "question": "Which?", "options": ["otd", "supplier_otd"]}') == \
        ClarifyDecision("Which?", ("otd", "supplier_otd"))
    assert parse_decision('{"action": "unsupported", "reason": "HR data"}') == UnsupportedDecision("HR data")


@pytest.mark.parametrize("reply", ["no json here", '{"action": "query"}', '["otd"]', '{"action": "dance"}'])
def test_invalid_replies_raise(reply: str) -> None:
    with pytest.raises(ModelOutputError):
        parse_decision(reply)
