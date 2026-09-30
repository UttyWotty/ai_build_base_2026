"""Command-line entry point that generates the synthetic plant into the data directory.

Seed, data directory, and catalog directory default to module-level constants read from the environment.
Running it twice with the same seed produces identical file contents (see the manifest fingerprints).
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.data_pipeline.synthetic.config import DEFAULT_SEED, GenerationConfig
from pdm_oee.data_pipeline.synthetic.sources import render_sources
from pdm_oee.data_pipeline.synthetic.world import build_world
from pdm_oee.data_pipeline.synthetic.writer import write_dataset

DATA_DIR = Path(os.getenv("PDM_DATA_DIR", "data/pdm"))
SEMANTIC_DIR = Path(os.getenv("PDM_SEMANTIC_DIR", "semantic/pdm"))
SYNTHETIC_SEED = int(os.getenv("PDM_SYNTHETIC_SEED", str(DEFAULT_SEED)))

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Generate the plant, render its sources, and write everything; returns a process exit code."""
    parser = argparse.ArgumentParser(description="Generate the synthetic plant dataset.")
    parser.add_argument("--seed", type=int, default=SYNTHETIC_SEED, help="random seed (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="output directory (default: %(default)s)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    catalog = load_catalog(SEMANTIC_DIR)
    config = GenerationConfig(seed=args.seed)
    world = build_world(config, catalog)
    sources = render_sources(world, catalog, config.seed)
    manifest = write_dataset(world, sources, config, args.out)
    logger.info("Wrote %d source files and %d truth tables to %s", len(sources), len(world.tables), args.out)
    logger.info("Manifest: %s", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
