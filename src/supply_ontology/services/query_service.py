"""Runs governed queries: compile a spec against the catalog, execute it on DuckDB, and return the result with provenance.

The data's as-of date is the latest inventory snapshot, the last complete week in the conformed layer.
Every result carries the compiled SQL, its fingerprint, and the metric definitions that produced it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.metric_model import Metric
from supply_ontology.core.query_spec import QuerySpec
from supply_ontology.core.sql_compiler import CompiledQuery, compile_query
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from supply_ontology.services.settings import CONFORMED_DIR

AS_OF_SQL = "SELECT max(snapshot_date) AS as_of FROM inventory_snapshot"


@dataclass(frozen=True)
class QueryResult:
    """A governed answer and everything needed to audit it."""

    spec: QuerySpec
    compiled: CompiledQuery
    metrics: tuple[Metric, ...]
    frame: pd.DataFrame
    as_of: date


class QueryService:
    """Compiles and executes query specs."""

    def __init__(
        self, catalog: SemanticCatalog, connection_manager: DuckDBConnectionManager | None = None,
        conformed_dir: Path = CONFORMED_DIR,
    ) -> None:
        self.catalog = catalog
        self.connection_manager = connection_manager or DuckDBConnectionManager(
            conformed_dir, list(catalog.ontology.entities)
        )
        self._as_of: date | None = None

    @property
    def as_of(self) -> date:
        """The data's as-of date, read once."""
        if self._as_of is None:
            value = self.connection_manager.execute(AS_OF_SQL)["as_of"].iloc[0]
            self._as_of = pd.Timestamp(value).date()
        return self._as_of

    def compile(self, spec: QuerySpec) -> CompiledQuery:
        """Compile without executing."""
        return compile_query(spec, self.catalog, self.as_of)

    def run(self, spec: QuerySpec) -> QueryResult:
        """Compile and execute a spec."""
        compiled = self.compile(spec)
        frame = self.connection_manager.execute(compiled.sql, compiled.parameters)
        metrics = tuple(self.catalog.metrics[m] for m in spec.metrics)
        return QueryResult(spec=spec, compiled=compiled, metrics=metrics, frame=frame, as_of=self.as_of)
