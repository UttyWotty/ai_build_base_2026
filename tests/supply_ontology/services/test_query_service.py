"""QueryService on the conformed small world: as-of detection, provenance, and agreement with an independent count.

The OTD value is recomputed directly with pandas from the conformed frame and must match the compiled SQL result.
Results must carry the metric definitions and the compiled fingerprint.
"""
from __future__ import annotations

from datetime import date

import pytest

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.query_spec_parser import parse_query_spec
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.data_pipeline.synthetic.world import World
from supply_ontology.services.query_service import QueryService


def test_as_of_is_the_last_snapshot(conformed_database: DuckDBConnectionManager, catalog: SemanticCatalog, small_world: World) -> None:
    service = QueryService(catalog, connection_manager=conformed_database)
    assert service.as_of == small_world.timeline.end


def test_otd_matches_an_independent_pandas_count(
    conformed_database: DuckDBConnectionManager, catalog: SemanticCatalog
) -> None:
    service = QueryService(catalog, connection_manager=conformed_database)
    result = service.run(parse_query_spec({"metrics": ["otd"]}))
    lines = conformed_database.execute("SELECT * FROM sales_order_line")
    due = lines[(lines["status"] != "cancelled") & (lines["committed_date"].dt.date <= service.as_of)]
    assert result.frame["otd"].iloc[0] == pytest.approx(due["is_delivered_complete_by_committed"].mean())
    assert [m.id for m in result.metrics] == ["otd"]
    assert len(result.compiled.fingerprint) == 16
    assert isinstance(result.as_of, date)
