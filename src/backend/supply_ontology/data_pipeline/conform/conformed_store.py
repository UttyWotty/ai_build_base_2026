"""Filesystem adapter for the conformed layer: one Parquet file per ontology entity.

The writer replaces the whole directory content for the given entities so stale files never linger.
Readers (the DuckDB adapter) locate entity files with entity_path.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PARQUET_SUFFIX = ".parquet"


def entity_path(conformed_dir: Path, entity: str) -> Path:
    """Location of an entity's Parquet file."""
    return conformed_dir / f"{entity}{PARQUET_SUFFIX}"


def write_conformed(tables: dict[str, pd.DataFrame], conformed_dir: Path) -> list[Path]:
    """Write every entity frame; return the written paths."""
    conformed_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for entity, frame in sorted(tables.items()):
        path = entity_path(conformed_dir, entity)
        frame.to_parquet(path, index=False, engine="pyarrow")
        written.append(path)
    return written
