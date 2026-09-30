"""Filesystem adapter for the conformed layer: one Parquet file per canonical entity.

Writing replaces the whole layer; reading returns the frames keyed by entity name.
The DuckDB adapter reads the same paths, so this module owns the naming rule.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PARQUET_SUFFIX = ".parquet"


def entity_path(conformed_dir: Path, entity: str) -> Path:
    return conformed_dir / f"{entity}{PARQUET_SUFFIX}"


def write_conformed(tables: dict[str, pd.DataFrame], conformed_dir: Path) -> list[Path]:
    conformed_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for entity, frame in sorted(tables.items()):
        path = entity_path(conformed_dir, entity)
        frame.to_parquet(path, index=False, engine="pyarrow")
        paths.append(path)
    return paths


def read_conformed(conformed_dir: Path, entities: list[str]) -> dict[str, pd.DataFrame]:
    return {entity: pd.read_parquet(entity_path(conformed_dir, entity), engine="pyarrow") for entity in entities}
