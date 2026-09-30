"""The consistency demo on the small world with scripted models, plus the raw source database's safety rules.

Naive replies are hand-written SQL over the raw exports, so the test controls how the teams disagree.
Governed replies are minimal specs; wording binds the metric and the calendar anchor fixes the period.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.demo_script import DEMO_PERIOD_ANCHOR, SAME_QUESTION
from supply_ontology.core.team_recipes import TeamRecipe, parse_recipes
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.llm_client import LLMError
from supply_ontology.data_pipeline.raw_source_database import (
    RawQueryError,
    RawSourceDatabase,
)
from supply_ontology.data_pipeline.semantic_files import load_yaml_document
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World
from supply_ontology.services.consistency_demo import ConsistencyDemo
from supply_ontology.services.demo_models import OUTCOME_ANSWER
from supply_ontology.services.demo_report import report_to_dict
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.recipe_comparison import compare_recipes
from tests.supply_ontology.services.scripted_model import ScriptedModel

REQUESTED_DATE_SQL = """```sql
SELECT avg(CASE WHEN CONFIRMED_DELIV_DATE <= REQ_DELIV_DATE THEN 1 ELSE 0 END) AS answer FROM erp_sales_order_items
```"""
ALL_LINES_SQL = "SELECT count(*) * 0 + 0.5 AS answer FROM erp_sales_order_items"
GOVERNED_REPLY = json.dumps({"action": "query", "spec": {"metrics": ["otd"]}})
BOUNDARY_REPLY = json.dumps({"action": "query", "spec": {"metrics": ["supplier_otd"]}})


RECIPES_FILE = Path(__file__).resolve().parents[3] / "demo" / "supply" / "team_recipes.yaml"


@pytest.fixture(scope="module")
def recipes(catalog: SemanticCatalog) -> tuple[TeamRecipe, ...]:
    return parse_recipes(load_yaml_document(RECIPES_FILE), catalog.vocabulary.personas, catalog.metrics)


@pytest.fixture(scope="module")
def raw_database(small_world: World) -> RawSourceDatabase:
    return RawSourceDatabase({s.relative_path: s.frame for s in render_sources(small_world)})


def build_demo(catalog: SemanticCatalog, database: DuckDBConnectionManager, raw: RawSourceDatabase,
               naive_replies: list[object], recipes: tuple[TeamRecipe, ...] = ()) -> ConsistencyDemo:
    governed_model = ScriptedModel([GOVERNED_REPLY] * 3 + [BOUNDARY_REPLY])
    service = NLService(catalog, QueryService(catalog, connection_manager=database), governed_model)
    return ConsistencyDemo(service, raw, ScriptedModel(naive_replies), recipes)


def test_raw_database_exposes_every_export_as_a_table(raw_database: RawSourceDatabase) -> None:
    names = {t.name for t in raw_database.tables}
    assert {"erp_sales_order_items", "tms_shipments", "mdm_partner_crosswalk"} <= names
    assert raw_database.run_select("SELECT count(*) AS n FROM erp_sales_order_items")["n"].iloc[0] > 0


def test_raw_database_refuses_files_and_bad_sql(raw_database: RawSourceDatabase) -> None:
    with pytest.raises(RawQueryError):
        raw_database.run_select("SELECT * FROM read_csv('/etc/hosts')")
    with pytest.raises(RawQueryError):
        raw_database.run_select("SELECT no_such_column FROM erp_sales_order_items")


def test_runaway_query_is_interrupted(small_world: World) -> None:
    raw = RawSourceDatabase({}, timeout_seconds=0.2)
    with pytest.raises(RawQueryError, match="exceeded"):
        raw.run_select("SELECT count(*) FROM range(1000000000) a, range(1000000000) b")


def test_demo_shows_disagreement_then_one_governed_answer(
    catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, raw_database: RawSourceDatabase,
) -> None:
    demo = build_demo(catalog, conformed_database, raw_database, [REQUESTED_DATE_SQL, ALL_LINES_SQL, "DROP TABLE x", "DROP TABLE y"])
    report = demo.run()
    assert [r.error is None for r in report.naive] == [True, True, False]
    assert [r.attempts for r in report.naive] == [1, 1, 2]
    assert not report.naive_agree and report.naive_spread is not None
    assert all(r.outcome == OUTCOME_ANSWER and r.metrics == ("otd",) for r in report.governed)
    assert report.governed_consistent and len(report.governed_fingerprints) == 1
    assert report.boundary_distinct and report.boundary.value != report.governed[0].value
    saved = json.loads(json.dumps(report_to_dict(report, "stub"), default=str))
    assert saved["verdicts"]["governed_consistent"] and saved["naive"][0]["rows"][0]["answer"] is not None


def test_naive_model_failure_is_recorded_not_raised(
    catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, raw_database: RawSourceDatabase,
) -> None:
    demo = build_demo(catalog, conformed_database, raw_database, [LLMError("connection refused")] * 3)
    report = demo.run()
    assert all("connection refused" in (r.error or "") for r in report.naive)
    assert not report.naive_agree and report.governed_consistent


def test_team_recipes_run_on_the_raw_sources_next_to_the_governed_answer(
    catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, raw_database: RawSourceDatabase,
    recipes: tuple[TeamRecipe, ...],
) -> None:
    query_service = QueryService(catalog, connection_manager=conformed_database)
    comparison = compare_recipes(recipes, raw_database, query_service)
    assert [run.error for run in comparison.runs] == [None, None, None]
    assert all(run.value is not None and 0.0 <= run.value <= 1.0 for run in comparison.runs)
    assert comparison.period == calendar_anchors(query_service.as_of)[DEMO_PERIOD_ANCHOR]
    assert comparison.governed_value is not None


def test_governed_reference_is_the_same_sql_the_personas_get(
    catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, raw_database: RawSourceDatabase,
    recipes: tuple[TeamRecipe, ...],
) -> None:
    demo = build_demo(catalog, conformed_database, raw_database, [ALL_LINES_SQL] * 3, recipes)
    report = demo.run()
    assert report.recipes is not None
    assert report.governed_fingerprints == (report.recipes.governed_fingerprint,)
    saved = json.loads(json.dumps(report_to_dict(report, "stub"), default=str))
    assert [run["persona"] for run in saved["recipes"]["runs"]] == ["planning", "procurement", "logistics"]


def test_failed_or_empty_naive_query_gets_one_retry_with_the_problem(
    catalog: SemanticCatalog, conformed_database: DuckDBConnectionManager, raw_database: RawSourceDatabase,
) -> None:
    demo = build_demo(catalog, conformed_database, raw_database, [])
    demo.llm_client = ScriptedModel(["SELECT nope FROM erp_sales_order_items", ALL_LINES_SQL,
                                     "SELECT NULL::DOUBLE AS answer", ALL_LINES_SQL])
    as_of = demo.nl_service.query_service.as_of
    fixed = demo.run_naive(SAME_QUESTION[0], as_of)
    assert fixed.value == 0.5 and fixed.attempts == 2 and fixed.error is None
    assert "nope" in demo.llm_client.calls[1][-1]["content"]
    emptied = demo.run_naive(SAME_QUESTION[1], as_of)
    assert emptied.value == 0.5 and "no value" in demo.llm_client.calls[3][-1]["content"]


def test_raw_schema_shows_the_full_range_of_date_columns(raw_database: RawSourceDatabase) -> None:
    items = next(t for t in raw_database.tables if t.name == "erp_sales_order_items")
    columns = {c.name: c for c in items.columns}
    low, high = columns["CREATED_ON"].value_range
    assert low < high and columns["STATUS"].value_range is None
