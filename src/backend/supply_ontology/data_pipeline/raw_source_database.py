"""Adapter exposing the raw source exports as DuckDB tables for the naive text-to-SQL baseline.

Each export becomes a view named after its path, the connection is locked so model-written SQL cannot touch files,
and every query runs under a time limit and returns at most a few rows; engine errors become RawQueryError.
"""
from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

import duckdb
import pandas as pd

from supply_ontology.core.naive_sql import (
    ISO_DATE_PATTERN,
    ColumnSchema,
    TableSchema,
    raw_table_name,
)
from supply_ontology.data_pipeline.conform.source_reader import read_sources
from supply_ontology.data_pipeline.duckdb_adapter import DuckDBConnectionManager

SAMPLE_VALUE_COUNT = 3
SAMPLE_VALUE_MAX_CHARS = 24
QUERY_TIMEOUT_SECONDS = 60.0
MAX_RESULT_ROWS = 20
LIMITED_SQL = "SELECT * FROM ({sql}) AS naive_answer LIMIT {rows}"


class RawQueryError(Exception):
    """A query over the raw sources failed, timed out, or was refused by the locked connection."""


class RawSourceDatabase:
    """The raw source exports, queryable but read-only."""

    def __init__(
        self, sources: Mapping[str, pd.DataFrame], connection_manager: DuckDBConnectionManager | None = None,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
    ) -> None:
        self.connection_manager = connection_manager or DuckDBConnectionManager()
        self.timeout_seconds = timeout_seconds
        self.tables = tuple(self._register(raw_table_name(path), frame) for path, frame in sorted(sources.items()))
        self.connection_manager.restrict_to_registered_data()

    @classmethod
    def from_directory(cls, sources_dir: Path) -> RawSourceDatabase:
        """Load every expected export under `sources_dir`."""
        return cls(read_sources(sources_dir))

    def run_select(self, sql: str, parameters: Sequence[object] = ()) -> pd.DataFrame:
        """Run one read-only statement with bound parameters (none by default) and return its first rows."""
        timer = threading.Timer(self.timeout_seconds, self.connection_manager.interrupt)
        timer.start()
        try:
            return self.connection_manager.execute(LIMITED_SQL.format(sql=sql, rows=MAX_RESULT_ROWS), parameters)
        except duckdb.InterruptException as error:
            raise RawQueryError(f"Query exceeded {self.timeout_seconds:.0f} seconds") from error
        except duckdb.Error as error:
            raise RawQueryError(str(error).splitlines()[0]) from error
        finally:
            timer.cancel()

    def _register(self, name: str, frame: pd.DataFrame) -> TableSchema:
        self.connection_manager.register_frame(name, frame)
        columns = tuple(ColumnSchema(str(c), str(frame[c].dtype), _samples(frame[c]), _date_range(frame[c]))
                        for c in frame.columns)
        return TableSchema(name=name, row_count=len(frame), columns=columns)


def _samples(column: pd.Series) -> tuple[str, ...]:
    values = column.dropna().drop_duplicates().head(SAMPLE_VALUE_COUNT)
    return tuple(str(v)[:SAMPLE_VALUE_MAX_CHARS] for v in values)


def _date_range(column: pd.Series) -> tuple[str, str] | None:
    """First and last value of a date column (real dates, or text that is all ISO dates), else None."""
    values = column.dropna()
    if values.empty:
        return None
    if pd.api.types.is_datetime64_any_dtype(values):
        return str(values.min()), str(values.max())
    if values.dtype != object or not values.astype(str).str.match(ISO_DATE_PATTERN).all():
        return None
    text = values.astype(str)
    return text.min()[:SAMPLE_VALUE_MAX_CHARS], text.max()[:SAMPLE_VALUE_MAX_CHARS]
