"""Golden tests: compiled SQL for every metric returns the hand-computed values from golden_world.py.

Specs cover plain totals, dimensions across join paths, time grains, filters, multiple metrics, and period-end behaviour.
The as-of rule and zero denominators get dedicated cases.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from supply_ontology.core.query_spec_parser import parse_query_spec
from supply_ontology.core.sql_compiler import compile_query
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from tests.supply_ontology.compiler.conftest import CATALOG
from tests.supply_ontology.compiler.golden_world import AS_OF


def run(database: DuckDBConnectionManager, raw: dict[str, object], as_of: date = AS_OF) -> pd.DataFrame:
    compiled = compile_query(parse_query_spec(raw), CATALOG, as_of)
    return database.execute(compiled.sql, compiled.parameters)


TOTALS = [
    ("otd", 3 / 4), ("otd_vs_request", 1 / 4), ("supplier_otd", 2 / 3), ("carrier_on_time", 1 / 3),
    ("fill_rate", 25 / 29), ("line_fill_rate", 3 / 4), ("order_fill_rate", 2 / 3),
    ("days_of_inventory", 11.0), ("landed_cost_per_unit", 12.0), ("purchase_price_per_unit", 10.0),
]


@pytest.mark.parametrize(("metric", "expected"), TOTALS)
def test_metric_totals(database: DuckDBConnectionManager, metric: str, expected: float) -> None:
    assert run(database, {"metrics": [metric]})[metric].iloc[0] == pytest.approx(expected)


def test_otd_by_customer_region_crosses_two_joins(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["otd"], "dimensions": ["customer.region"]})
    assert dict(zip(frame["customer__region"], frame["otd"])) == {"EU": 1.0, "NA": pytest.approx(2 / 3)}


def test_otd_by_month_uses_committed_date_and_skips_cancelled(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["otd"], "time_grain": "month"})
    assert frame["otd"].tolist() == [1.0, 0.0, 1.0]
    assert frame["otd__denominator"].tolist() == [2, 1, 1]


def test_filter_on_joined_dimension(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["otd"], "filters": [{"dimension": "plant.plant_id", "operator": "in", "value": ["US01"]}]})
    assert frame["otd"].iloc[0] == pytest.approx(2 / 3)


def test_supplier_otd_by_supplier(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["supplier_otd"], "dimensions": ["supplier.supplier_id"]})
    assert frame["supplier_otd"].tolist() == [0.5, 1.0]


def test_landed_cost_by_supplier_through_po_line(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["landed_cost_per_unit", "purchase_price_per_unit"], "dimensions": ["supplier.supplier_id"]})
    assert frame["landed_cost_per_unit"].tolist() == [15.0, 11.0]
    assert frame["purchase_price_per_unit"].tolist() == [10.0, 10.0]


def test_days_of_inventory_takes_the_last_snapshot_of_each_period(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["days_of_inventory"], "time_grain": "month"})
    assert frame["days_of_inventory"].tolist() == [6.0, 11.0]
    january = run(database, {"metrics": ["days_of_inventory"], "time_range": {"start": "2026-01-01", "end": "2026-01-31"}})
    assert january["days_of_inventory"].iloc[0] == 6.0


def test_zero_denominator_is_null_not_an_error(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["days_of_inventory"], "dimensions": ["part.part_id"], "time_grain": "month"})
    values = {(p, str(m.date())): v for p, m, v in zip(frame["part__part_id"], frame["period"], frame["days_of_inventory"])}
    assert values[("P1", "2026-01-01")] == 8.0 and values[("P2", "2026-02-01")] == 6.0
    assert pd.isna(values[("P3", "2026-02-01")])


def test_multiple_metrics_share_dimension_rows(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["otd", "fill_rate"], "dimensions": ["customer.region"]})
    assert frame["customer__region"].tolist() == ["EU", "NA"]
    assert frame["fill_rate"].tolist() == [1.0, pytest.approx(20 / 24)]


def test_rows_after_as_of_have_no_outcome_yet(database: DuckDBConnectionManager) -> None:
    frame = run(database, {"metrics": ["otd"]}, as_of=date(2026, 2, 28))
    assert frame["otd"].iloc[0] == pytest.approx(2 / 3)
