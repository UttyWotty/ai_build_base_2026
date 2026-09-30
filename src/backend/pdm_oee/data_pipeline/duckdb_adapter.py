"""DuckDB adapter: an in-memory database exposing each conformed entity as a view over its Parquet file.

Views keep the database file-free and portable; the same code works from any checkout location.
All query execution goes through execute(), which binds parameters and returns a pandas frame.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import pandas as pd

from pdm_oee.core.identifiers import is_valid_identifier
from pdm_oee.data_pipeline.conform.conformed_store import entity_path
from pdm_oee.data_pipeline.conform.errors import ConformError

IN_MEMORY = ":memory:"


class DuckDBConnectionManager:
    """Owns one DuckDB connection with a view per entity."""

    def __init__(self, conformed_dir: Path | None = None, entities: Sequence[str] = ()) -> None:
        self.connection = duckdb.connect(IN_MEMORY)
        if conformed_dir is not None:
            for entity in entities:
                self.register_parquet(entity, entity_path(conformed_dir, entity))

    def register_parquet(self, name: str, path: Path) -> None:
        """Create or replace a view named `name` over a Parquet file."""
        if not is_valid_identifier(name):
            raise ConformError(f"Invalid view name '{name}'")
        if not path.exists():
            raise ConformError(f"Conformed file not found: {path}. Run `make conform` first.")
        escaped = str(path.resolve()).replace("'", "''")
        self.connection.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{escaped}')")

    def register_frame(self, name: str, frame: pd.DataFrame) -> None:
        """Expose an in-memory frame as a view (used by tests and services)."""
        if not is_valid_identifier(name):
            raise ConformError(f"Invalid table name '{name}'")
        self.connection.register(f"{name}__frame", frame)
        self.connection.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {name}__frame")

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> pd.DataFrame:
        """Run a query with bound parameters and return the result."""
        return self.connection.execute(sql, list(parameters)).fetchdf()

    def close(self) -> None:
        self.connection.close()
