"""OEE, loss, and reliability answers over the conformed layer, for any grouping and period.

Measures are computed once per service from the DuckDB views and filtered by shift start for each question.
Groupings are asset, line, site, asset class, shift date, ISO week, or month; periods are half-open [start, end).
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.loss_waterfall import loss_minutes, waterfall
from pdm_oee.core.metric_rollup import rollup
from pdm_oee.core.reliability_measures import component_measures, preventive_measures
from pdm_oee.core.shift_measures import shift_measures, split_by_shift
from pdm_oee.data_pipeline.conform.pipeline import ENTITIES
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.settings import CONFORMED_DIR

GROUPINGS = ("asset_id", "line_id", "site_id", "asset_class", "shift_date", "week", "month")
TABLE_SQL = "SELECT * FROM {table}"
WEEK_FORMAT = "%G-W%V"
MONTH_FORMAT = "%Y-%m"


class OEEService:
    """Answers metric and loss questions from the conformed tables."""

    def __init__(self, catalog: PlantCatalog, connection_manager: DuckDBConnectionManager | None = None) -> None:
        self.catalog = catalog
        self.connection_manager = connection_manager or DuckDBConnectionManager(CONFORMED_DIR, list(ENTITIES))
        tables = {name: self.connection_manager.execute(TABLE_SQL.format(table=name)) for name in
                  ("machine_state", "shift", "asset", "production_count", "routing", "failure_event", "work_order", "component")}
        self.tables = tables
        self.pieces = split_by_shift(tables["machine_state"], tables["shift"], tables["asset"])
        measures = shift_measures(tables["machine_state"], tables["shift"], tables["asset"], tables["production_count"],
                                  tables["routing"], catalog)
        measures = measures.merge(tables["asset"][["asset_id", "line_id"]], on="asset_id")
        measures = measures.merge(tables["shift"][["shift_id", "shift_date"]], on="shift_id")
        dates = pd.to_datetime(measures["shift_date"])
        measures["week"], measures["month"] = dates.dt.strftime(WEEK_FORMAT), dates.dt.strftime(MONTH_FORMAT)
        self.measures = measures
        self.losses = loss_minutes(self.pieces, measures, catalog)

    def period(self, start: date | None = None, end: date | None = None) -> pd.Series:
        """Rows of the measure frame whose shift date is in [start, end)."""
        dates = pd.to_datetime(self.measures["shift_date"]).dt.date
        keep = pd.Series(True, index=self.measures.index)
        if start is not None:
            keep &= dates >= start
        if end is not None:
            keep &= dates < end
        return keep

    def metrics(self, metric_ids: Sequence[str], group_by: Sequence[str] = (), start: date | None = None,
                end: date | None = None, filters: dict[str, str] | None = None) -> pd.DataFrame:
        """Asset-shift metrics (OEE family) rolled up by the grouping over the period."""
        rows = self._selected(start, end, filters)
        return rollup(self.measures[rows], self.catalog, metric_ids, list(group_by))

    def loss_waterfall(self, start: date | None = None, end: date | None = None,
                       filters: dict[str, str] | None = None) -> pd.DataFrame:
        rows = self._selected(start, end, filters)
        return waterfall(self.measures[rows], self.losses[rows], self.catalog)

    def reliability(self, start: date, end: date, group_by: Sequence[str] = ("asset_id", "component")) -> pd.DataFrame:
        frame = component_measures(self.tables["machine_state"], self.tables["failure_event"], self.tables["component"],
                                   pd.Timestamp(start), pd.Timestamp(end))
        return rollup(frame, self.catalog, ["mtbf", "mttr"], list(group_by))

    def pm_compliance(self, start: date, end: date, group_by: Sequence[str] = ("asset_id",)) -> pd.DataFrame:
        frame = preventive_measures(self.tables["work_order"], self.tables["asset"], start, end)
        return rollup(frame, self.catalog, ["pm_compliance"], list(group_by))

    def performance_anomalies(self) -> pd.DataFrame:
        """Asset-shifts with performance above 100%, which means a wrong ideal cycle time."""
        return self.measures[self.measures["ideal_run_time"] > self.measures["run_time"]][["asset_id", "shift_id", "product_id"]]

    def _selected(self, start: date | None, end: date | None, filters: dict[str, str] | None) -> pd.Series:
        rows = self.period(start, end)
        for column, value in (filters or {}).items():
            rows &= self.measures[column] == value
        return rows
