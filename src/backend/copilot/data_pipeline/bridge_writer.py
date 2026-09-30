"""Writes the generated bridge data: the spare catalog, stock movements, spare purchase orders, and a manifest.

Tables are Parquet files under the bridge data directory, one per entity, so the world store can expose them as views.
The manifest records the seed and the story facts the demo depends on, in the same spirit as the worlds' manifests.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

MANIFEST_FILENAME = "manifest.json"
JSON_INDENT = 2


def write_bridge_tables(tables: Mapping[str, pd.DataFrame], manifest: Mapping[str, object], out_dir: Path) -> list[Path]:
    """Write each table as <name>.parquet and the manifest as JSON; return the written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, frame in sorted(tables.items()):
        path = out_dir / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        paths.append(path)
    manifest_path = out_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=JSON_INDENT, default=str) + "\n", encoding="utf-8")
    return paths + [manifest_path]
