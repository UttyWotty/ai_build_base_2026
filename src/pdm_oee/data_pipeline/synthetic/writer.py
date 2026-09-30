"""Filesystem adapter that writes a generated plant: source system files, canonical truth tables, and a manifest.

Sources land under sources/<system>/ in their native format; truth tables land under truth/ as Parquet, one per entity.
The manifest records the seed, the configuration, the story facts, and a content fingerprint and row count per file.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from pdm_oee.data_pipeline.synthetic.config import GenerationConfig
from pdm_oee.data_pipeline.synthetic.fingerprint import frame_fingerprint
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from pdm_oee.data_pipeline.synthetic.world import World

SOURCES_DIRNAME = "sources"
TRUTH_DIRNAME = "truth"
MANIFEST_FILENAME = "manifest.json"
PARQUET_SUFFIX = ".parquet"
JSON_INDENT = 2
FILE_ENCODING = "utf-8"


def write_dataset(world: World, sources: list[SourceFile], config: GenerationConfig, out_dir: Path) -> Path:
    """Write every file and the manifest under `out_dir`; return the manifest path."""
    entries = {}
    for source in sources:
        relative = f"{SOURCES_DIRNAME}/{source.relative_path}"
        _write_frame(source.frame, out_dir / relative, source.file_format)
        entries[relative] = _entry(source.frame)
    for entity, frame in sorted(world.tables.items()):
        relative = f"{TRUTH_DIRNAME}/{entity}{PARQUET_SUFFIX}"
        _write_frame(frame, out_dir / relative, FileFormat.PARQUET)
        entries[relative] = _entry(frame)
    manifest = {
        "seed": config.seed, "horizon_start": config.horizon_start.isoformat(),
        "scale": asdict(config.scale), "stories": asdict(config.stories),
        "story_facts": asdict(world.story_facts), "files": entries,
    }
    path = out_dir / MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, indent=JSON_INDENT, sort_keys=True) + "\n", encoding=FILE_ENCODING)
    return path


def _entry(frame: pd.DataFrame) -> dict[str, object]:
    return {"rows": len(frame), "fingerprint": frame_fingerprint(frame)}


def _write_frame(frame: pd.DataFrame, path: Path, file_format: FileFormat) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if file_format == FileFormat.PARQUET:
        frame.to_parquet(path, index=False, engine="pyarrow")
    else:
        frame.to_excel(path, index=False, engine="openpyxl")
