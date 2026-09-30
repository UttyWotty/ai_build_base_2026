"""Command-line entry point that conforms data/sources into data/conformed, one Parquet file per canonical entity.

Directories default to module-level constants read from the environment; the catalog and mappings come from semantic/.
Any source value the governed mappings do not explain stops the run with a ConformError.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from pdm_oee.data_pipeline.conform.conformed_store import write_conformed
from pdm_oee.data_pipeline.conform.pipeline import conform_sources
from pdm_oee.data_pipeline.conform.source_reader import read_sources
from pdm_oee.data_pipeline.semantic_files import load_catalog, load_source_mappings

DATA_DIR = Path(os.getenv("PDM_DATA_DIR", "data/pdm"))
SEMANTIC_DIR = Path(os.getenv("PDM_SEMANTIC_DIR", "semantic/pdm"))
SOURCES_DIRNAME = "sources"
CONFORMED_DIRNAME = "conformed"

logger = logging.getLogger(__name__)


def main() -> int:
    """Read, conform, and write; returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    catalog = load_catalog(SEMANTIC_DIR)
    mappings = load_source_mappings(SEMANTIC_DIR, catalog)
    tables = conform_sources(read_sources(DATA_DIR / SOURCES_DIRNAME), catalog, mappings)
    paths = write_conformed(tables, DATA_DIR / CONFORMED_DIRNAME)
    logger.info("Wrote %d conformed tables to %s", len(paths), DATA_DIR / CONFORMED_DIRNAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
