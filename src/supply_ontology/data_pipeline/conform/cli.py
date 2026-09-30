"""Command-line entry point that conforms data/sources into data/conformed using the governed ontology.

The trailing window for days of inventory is read from the days_of_inventory metric's parameters, not hard-coded.
Paths default to module-level constants read from the environment.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from supply_ontology.data_pipeline.conform.conformed_store import write_conformed
from supply_ontology.data_pipeline.conform.errors import ConformError
from supply_ontology.data_pipeline.conform.pipeline import conform_sources
from supply_ontology.data_pipeline.conform.source_reader import read_sources
from supply_ontology.data_pipeline.semantic_files import load_catalog

DATA_DIR = Path(os.getenv("SUPPLY_DATA_DIR", "data/supply"))
SEMANTIC_DIR = Path(os.getenv("SUPPLY_SEMANTIC_DIR", "semantic/supply"))
SOURCES_DIRNAME = "sources"
CONFORMED_DIRNAME = "conformed"
DOI_METRIC = "days_of_inventory"
TRAILING_WINDOW_PARAMETER = "trailing_window_days"

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Conform sources and write the conformed layer; returns a process exit code."""
    parser = argparse.ArgumentParser(description="Conform source exports into ontology entities.")
    parser.add_argument("--data", type=Path, default=DATA_DIR, help="data directory (default: %(default)s)")
    parser.add_argument("--semantic", type=Path, default=SEMANTIC_DIR, help="semantic layer (default: %(default)s)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    catalog = load_catalog(args.semantic)
    doi = catalog.metric(DOI_METRIC)
    if doi is None or TRAILING_WINDOW_PARAMETER not in doi.parameters:
        raise ConformError(f"Metric {DOI_METRIC} must declare parameter {TRAILING_WINDOW_PARAMETER}")
    sources = read_sources(args.data / SOURCES_DIRNAME)
    tables = conform_sources(sources, catalog.ontology, int(doi.parameters[TRAILING_WINDOW_PARAMETER]))
    written = write_conformed(tables, args.data / CONFORMED_DIRNAME)
    logger.info("Conformed %d entities into %s", len(written), args.data / CONFORMED_DIRNAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
