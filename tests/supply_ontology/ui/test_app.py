"""The real Streamlit page, run headless with the small world and a scripted model injected through session state.

Covers the first render (no model call), a governed answer with its definition and SQL, and a clarification choice.
AppTest runs the script in-process, so no server is started.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.raw_source_database import RawSourceDatabase
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.recipe_comparison import compare_recipes
from supply_ontology.services.service_factory import RECIPES_FILE, load_team_recipes
from supply_ontology.ui.resources import (
    CATALOG_KEY,
    LLM_CLIENT_KEY,
    QUERY_SERVICE_KEY,
    RECIPE_COMPARISON_KEY,
)
from tests.supply_ontology.services.scripted_model import ScriptedModel

APP_PATH = Path(__file__).resolve().parents[3] / "src" / "supply_ontology" / "ui" / "app.py"
TIMEOUT_SECONDS = 30
OTD_REPLY = json.dumps({"action": "query", "spec": {"metrics": ["otd"]}})
CLARIFY_REPLY = json.dumps({"action": "clarify", "question": "Which on-time do you mean?",
                            "options": ["otd", "supplier_otd", "carrier_on_time"]})
SUPPLIER_REPLY = json.dumps({"action": "query", "spec": {"metrics": ["supplier_otd"]}})


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def small_comparison(catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, small_world: World):
    raw = RawSourceDatabase({s.relative_path: s.frame for s in render_sources(small_world)})
    recipes = load_team_recipes(catalog, REPO_ROOT / RECIPES_FILE)
    return compare_recipes(recipes, raw, QueryService(catalog, connection_manager=conformed_database))


@pytest.fixture
def app(catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, small_comparison):
    def start(replies: list[object]) -> tuple[AppTest, ScriptedModel]:
        model = ScriptedModel(replies)
        page = AppTest.from_file(str(APP_PATH), default_timeout=TIMEOUT_SECONDS)
        page.session_state[CATALOG_KEY] = catalog
        page.session_state[QUERY_SERVICE_KEY] = QueryService(catalog, connection_manager=conformed_database)
        page.session_state[RECIPE_COMPARISON_KEY] = small_comparison
        page.session_state[LLM_CLIENT_KEY] = model
        return page.run(), model
    return start


def test_first_render_shows_tabs_and_never_calls_the_model(app) -> None:
    page, model = app([])
    assert not page.exception
    assert [t.label for t in page.tabs] == ["Ask", "Consistency demo", "Metric catalog"]
    assert model.calls == []


def test_demo_tab_shows_team_recipes_next_to_the_governed_answer(app) -> None:
    page, model = app([])
    headers = [s.value for s in page.subheader]
    assert "The problem, reproduced: each team's own recipe" in headers
    table = page.dataframe[0].value
    assert list(table["Team"]) == ["planning", "procurement", "logistics", "governed"]
    assert table["Effectively computes"].iloc[0] == "otd_vs_request" and model.calls == []


def test_question_shows_value_definition_and_sql(app) -> None:
    page, model = app([OTD_REPLY])
    page.sidebar.selectbox[0].select("planning").run()
    page.text_input[0].input("What was our service level last quarter?")
    page.button[-1].click().run()
    assert not page.exception and len(model.calls) == 1
    assert page.metric[0].label == "On-time delivery (customer)" and page.metric[0].value.endswith("%")
    captions = " ".join(c.value for c in page.caption)
    assert "chosen by the wording (service level)" in captions
    labels = [e.label for e in page.expander]
    assert any(label.startswith("Definition: On-time delivery") for label in labels)
    assert any(label.startswith("SQL (fingerprint") for label in labels)


def test_clarification_choice_asks_again_with_the_metric_bound(app) -> None:
    page, model = app([CLARIFY_REPLY, SUPPLIER_REPLY])
    page.text_input[0].input("How are we doing on time?")
    page.button[-1].click().run()
    assert page.info[0].value == "Which on-time do you mean?"
    choice = next(b for b in page.button if b.key == "clarify-supplier_otd")
    choice.click().run()
    assert not page.exception
    assert model.calls[1][-1]["content"].count("supplier_otd") >= 1
    assert page.metric[0].label.startswith("Supplier")


def render_demo_page(report: dict[str, object]) -> None:
    from supply_ontology.ui.demo_view import render_saved_demo

    render_saved_demo({"stub-model": report})


def governed_run(persona: str, metric: str, value: float) -> dict[str, object]:
    return {"persona": persona, "question": f"{persona} question", "outcome": "answer", "metrics": [metric],
            "resolved_by": "wording", "value": value, "fingerprint": "abc123def4567890", "sql": "SELECT 1", "detail": None}


def test_saved_demo_run_replays_all_three_parts() -> None:
    report = {
        "model": "stub-model", "as_of": "2026-09-27",
        "verdicts": {"naive_agree": False, "naive_spread": 0.17, "governed_consistent": True,
                     "governed_fingerprints": ["abc123def4567890"], "boundary_distinct": True},
        "naive": [{"persona": "planning", "question": "q", "reply": "r", "sql": "SELECT 0.61 AS answer",
                   "value": 0.61, "error": None, "rows": [{"answer": 0.61}]},
                  {"persona": "logistics", "question": "q", "reply": "r", "sql": None, "value": None,
                   "error": "Only SELECT or WITH queries are accepted.", "rows": None, "attempts": 2}],
        "governed": [governed_run("planning", "otd", 0.78), governed_run("logistics", "otd", 0.78)],
        "boundary": governed_run("logistics", "supplier_otd", 0.66),
    }
    page = AppTest.from_function(render_demo_page, kwargs={"report": report}, default_timeout=TIMEOUT_SECONDS).run()
    assert not page.exception
    assert [s.value for s in page.subheader][0].startswith("1. The problem")
    text = " ".join(m.value for m in page.markdown)
    assert "Answers agree:** no, spread 17.0 points" in text and "One SQL fingerprint and one answer:** yes" in text
    assert page.error[0].value == "Only SELECT or WITH queries are accepted."
    assert any("after 2 attempts" in e.label for e in page.expander)
