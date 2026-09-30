"""Command-line entry point that generates the synthetic dataset into the data directory.

Seed and output directory default to module-level constants read from the environment, and can be overridden by flags.
Running it twice with the same seed produces identical file contents (see the manifest fingerprints).
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from supply_ontology.data_pipeline.synthetic.config import (
    DEFAULT_SEED,
    GenerationConfig,
)
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import build_world
from supply_ontology.data_pipeline.synthetic.writer import write_dataset

DATA_DIR = Path(os.getenv("SUPPLY_DATA_DIR", "data/supply"))
SYNTHETIC_SEED = int(os.getenv("SUPPLY_SYNTHETIC_SEED", str(DEFAULT_SEED)))

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Generate the world, render its sources, and write everything; returns a process exit code."""
    parser = argparse.ArgumentParser(description="Generate the synthetic supply chain dataset.")
    parser.add_argument("--seed", type=int, default=SYNTHETIC_SEED, help="random seed (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="output directory (default: %(default)s)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = GenerationConfig(seed=args.seed)
    world = build_world(config)
    sources = render_sources(world)
    manifest = write_dataset(world, sources, config, args.out)
    logger.info("Wrote %d source files and %d truth tables to %s", len(sources), len(world.tables), args.out)
    logger.info("Degrading supplier: %s", world.story_facts.degrading_supplier_id)
    logger.info("Manifest: %s", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
