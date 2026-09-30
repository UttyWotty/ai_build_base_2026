"""NLService behaviour with a scripted stub model on the conformed small world.

The stub returns canned replies in order and records every message list it receives.
Cases cover binding overrides, grounding, retries, clarifications, unknown filter values, and an unreachable model.
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.llm_client import LLMError
from supply_ontology.services.nl_models import (
    MODEL_UNAVAILABLE,
    RESOLVED_BY_MODEL,
    RESOLVED_BY_WORDING,
    Answer,
    Clarification,
    Unanswerable,
)
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.query_service import QueryService
from tests.supply_ontology.services.scripted_model import ScriptedModel


def query(spec: dict[str, object]) -> str:
    return json.dumps({"action": "query", "spec": spec})


@pytest.fixture
def make_service(catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager):
    def build(replies: Sequence[object]) -> tuple[NLService, ScriptedModel]:
        model = ScriptedModel(replies)
        return NLService(catalog, QueryService(catalog, connection_manager=conformed_database), model), model
    return build


def test_wording_overrides_the_models_metric_and_grounding_drops_extras(make_service) -> None:
    service, _ = make_service([query({"metrics": ["fill_rate"], "dimensions": ["part.category"], "time_grain": "month"})])
    answer = service.ask("What was our service level last quarter?", "planning")
    assert isinstance(answer, Answer) and answer.resolved_by == RESOLVED_BY_WORDING
    spec = answer.result.spec
    assert spec.metrics == ("otd",) and spec.dimensions == () and spec.time_grain is None
    assert spec.time_range is not None and len(answer.result.frame) == 1


def test_three_personas_same_fingerprint(make_service) -> None:
    fingerprints = set()
    for persona, question in [("planning", "What was our service level last quarter?"),
                              ("procurement", "How did customer delivery performance look last quarter?"),
                              ("logistics", "What was the customer on time delivery rate last quarter?")]:
        service, _ = make_service([query({"metrics": ["otd"]})])
        answer = service.ask(question, persona)
        assert isinstance(answer, Answer)
        fingerprints.add(answer.result.compiled.fingerprint)
    assert len(fingerprints) == 1


def test_invalid_reply_gets_one_retry_with_the_problem(make_service) -> None:
    service, model = make_service(["not json", query({"metrics": ["otd"]})])
    answer = service.ask("OTD", None)
    assert isinstance(answer, Answer) and len(answer.model_replies) == 2
    assert "JSON object" in model.calls[1][-1]["content"]


def test_second_invalid_reply_gives_up(make_service) -> None:
    service, _ = make_service(["nope", "still nope"])
    response = service.ask("OTD", None)
    assert isinstance(response, Unanswerable) and "after retry" in response.reason


def test_unsettled_ambiguity_becomes_a_clarification(make_service) -> None:
    service, _ = make_service([json.dumps({"action": "clarify", "question": "Which on-time?", "options": ["otd", "supplier_otd", "carrier_on_time"]})])
    response = service.ask("How are we doing on time?", None)
    assert isinstance(response, Clarification) and response.options == ("otd", "supplier_otd", "carrier_on_time")


def test_model_may_settle_ambiguity_only_within_the_candidates(make_service) -> None:
    service, _ = make_service([query({"metrics": ["fill_rate"]}), query({"metrics": ["carrier_on_time"]})])
    answer = service.ask("How are we doing on time?", None)
    assert isinstance(answer, Answer) and answer.resolved_by == RESOLVED_BY_MODEL
    assert answer.result.spec.metrics == ("carrier_on_time",)


def test_metric_clarification_is_refused_when_wording_binds(make_service) -> None:
    service, model = make_service([json.dumps({"action": "clarify", "question": "Which?", "options": ["otd", "supplier_otd"]}),
                                   query({"metrics": ["otd"]})])
    assert isinstance(service.ask("OTD last quarter", None), Answer)
    assert "already binds otd" in model.calls[1][-1]["content"]


def test_unknown_filter_value_suggests_close_matches(make_service) -> None:
    service, model = make_service([
        query({"metrics": ["otd"], "filters": [{"dimension": "plant.plant_id", "operator": "equals", "value": "US1"}]}),
        query({"metrics": ["otd"], "filters": [{"dimension": "plant.plant_id", "operator": "equals", "value": "US01"}]}),
    ])
    assert isinstance(service.ask("OTD for plant US1", None), Answer)
    assert "did you mean US01" in model.calls[1][-1]["content"]


def test_unreachable_model_is_reported(make_service) -> None:
    service, _ = make_service([LLMError("connection refused")])
    response = service.ask("OTD", None)
    assert isinstance(response, Unanswerable) and "connection refused" in response.reason
    assert response.kind == MODEL_UNAVAILABLE


def test_system_prompt_is_shared_across_personas(make_service) -> None:
    service, model = make_service([query({"metrics": ["otd"]}), query({"metrics": ["otd"]})])
    service.ask("OTD", "planning")
    service.ask("OTD", "logistics")
    assert model.calls[0][0] == model.calls[1][0]
