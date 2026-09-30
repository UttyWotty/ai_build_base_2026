"""Compiler guarantees beyond values: determinism, parameter binding, validation messages, and spec parsing.

Identical specs must produce byte-identical SQL and fingerprints; user values must never appear in SQL text.
Invalid specs must fail with messages specific enough to hand back to a language model.
"""
from __future__ import annotations

import pandas as pd
import pytest

from supply_ontology.core.errors import QueryValidationError, SemanticParseError
from supply_ontology.core.query_spec_parser import parse_query_spec
from supply_ontology.core.sql_compiler import compile_query
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from tests.supply_ontology.compiler.conftest import CATALOG
from tests.supply_ontology.compiler.golden_world import AS_OF
from tests.supply_ontology.compiler.test_golden_metrics import run

SPEC = {"metrics": ["otd"], "dimensions": ["customer.region"], "time_grain": "quarter",
        "filters": [{"dimension": "plant.plant_id", "operator": "equals", "value": "US01"}]}


def _issues(raw: dict[str, object]) -> list[str]:
    with pytest.raises(QueryValidationError) as raised:
        compile_query(parse_query_spec(raw), CATALOG, AS_OF)
    return [issue.message for issue in raised.value.issues]


def test_same_spec_same_sql_and_fingerprint() -> None:
    first = compile_query(parse_query_spec(SPEC), CATALOG, AS_OF)
    second = compile_query(parse_query_spec(dict(SPEC)), CATALOG, AS_OF)
    assert first.sql == second.sql and first.fingerprint == second.fingerprint
    assert first.key_columns == ("customer__region", "period")


def test_values_are_bound_not_inlined(database: DuckDBConnectionManager) -> None:
    hostile = "US01' OR '1'='1"
    raw = {"metrics": ["otd"], "filters": [{"dimension": "plant.plant_id", "operator": "equals", "value": hostile}]}
    compiled = compile_query(parse_query_spec(raw), CATALOG, AS_OF)
    assert hostile not in compiled.sql and hostile in compiled.parameters
    frame = run(database, raw)
    assert frame["otd__denominator"].iloc[0] == 0 and pd.isna(frame["otd"].iloc[0])


def test_unknown_metric_lists_the_choices() -> None:
    message = _issues({"metrics": ["on_time_delivery"]})[0]
    assert "unknown metric 'on_time_delivery'" in message and "otd" in message


def test_unreachable_dimension_is_explained() -> None:
    assert _issues({"metrics": ["otd"], "dimensions": ["supplier.region"]}) == [
        "'supplier.region' cannot be reached from grain 'sales_order_line'"
    ]


def test_dimension_must_reach_every_metric() -> None:
    assert _issues({"metrics": ["otd", "supplier_otd"], "dimensions": ["customer.region"]}) == [
        "'customer.region' cannot be reached from grain 'purchase_order_line'"
    ]


def test_filter_type_and_range_problems() -> None:
    issues = _issues({"metrics": ["otd"], "time_range": {"start": "2026-05-01", "end": "2026-04-01"},
                      "filters": [{"dimension": "sales_order_line.qty_ordered", "operator": "equals", "value": "ten"}]})
    assert issues == ["filter on 'sales_order_line.qty_ordered': value 'ten' is not a integer", "time_range start is after its end"]


def test_parser_rejects_malformed_specs() -> None:
    with pytest.raises(SemanticParseError, match="entity.attribute"):
        parse_query_spec({"metrics": ["otd"], "dimensions": ["region"]})
    with pytest.raises(SemanticParseError, match="not an ISO date"):
        parse_query_spec({"metrics": ["otd"], "time_range": {"start": "last quarter", "end": "2026-01-01"}})
    with pytest.raises(SemanticParseError, match="unknown field"):
        parse_query_spec({"metrics": ["otd"], "group_by": ["customer.region"]})


def test_spec_round_trips_through_dict() -> None:
    spec = parse_query_spec({**SPEC, "time_range": {"start": "2026-01-01", "end": "2026-03-31"}})
    assert parse_query_spec(spec.to_dict()) == spec
