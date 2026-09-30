"""One in-memory DuckDB database with views over the plant, the supply network, and the generated bridge data.

Views are prefixed by world (plant_, supply_, bridge_) so a query can join across them without name clashes.
Missing directories are skipped, so the store also serves the bridge builder before any bridge data exists.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import pandas as pd

from copilot.core.errors import CopilotError

IN_MEMORY = ":memory:"
PARQUET_SUFFIX = ".parquet"
PLANT_PREFIX = "plant_"
SUPPLY_PREFIX = "supply_"
BRIDGE_PREFIX = "bridge_"


class WorldStoreError(CopilotError):
    """A required table is missing from the store."""


class WorldStore:
    """Read access to both worlds and the bridge."""

    def __init__(self, plant_dir: Path | None, supply_dir: Path | None, bridge_dir: Path | None) -> None:
        self.connection = duckdb.connect(IN_MEMORY)
        self.views: set[str] = set()
        for prefix, directory in ((PLANT_PREFIX, plant_dir), (SUPPLY_PREFIX, supply_dir), (BRIDGE_PREFIX, bridge_dir)):
            if directory is not None and directory.exists():
                for path in sorted(directory.glob("*" + PARQUET_SUFFIX)):
                    self._register(prefix + path.stem, path)

    def _register(self, name: str, path: Path) -> None:
        escaped = str(path.resolve()).replace("'", "''")
        self.connection.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{escaped}')")
        self.views.add(name)

    def register_frame(self, name: str, frame: pd.DataFrame) -> None:
        """Expose an in-memory frame as a view (used by tests)."""
        self.connection.register(f"{name}__frame", frame)
        self.connection.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {name}__frame")
        self.views.add(name)

    def require(self, names: Sequence[str]) -> None:
        """Fail with the missing view names and how to build them."""
        missing = sorted(set(names) - self.views)
        if missing:
            raise WorldStoreError(f"Missing tables: {', '.join(missing)}. Run `make data` and `make bridge` first.")

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> pd.DataFrame:
        """Run a query with bound parameters and return the result."""
        return self.connection.execute(sql, list(parameters)).fetchdf()

    def close(self) -> None:
        self.connection.close()
