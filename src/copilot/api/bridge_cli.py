"""Command line that validates the bridge against both worlds and generates the spares history into data/bridge.

Both worlds must be generated and conformed first (`make data`); the bridge seed defaults to services.settings.
It prints the written files and how often each site needed an emergency buy.
"""
from __future__ import annotations

import argparse
import logging

from copilot.data_pipeline.bridge_files import load_bridge
from copilot.data_pipeline.bridge_writer import write_bridge_tables
from copilot.data_pipeline.world_store import WorldStore
from copilot.services.bridge_builder import BridgeBuilder
from copilot.services.settings import (
    BRIDGE_DATA_DIR,
    BRIDGE_SEED,
    BRIDGE_SEMANTIC_DIR,
    PLANT_CONFORMED_DIR,
    PLANT_SEMANTIC_DIR,
    SUPPLY_CONFORMED_DIR,
)
from pdm_oee.data_pipeline.semantic_files import load_catalog

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Build and write the bridge data."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate the bridge data (spares history) from both worlds.")
    parser.add_argument("--seed", type=int, default=BRIDGE_SEED)
    args = parser.parse_args(argv)
    store = WorldStore(PLANT_CONFORMED_DIR, SUPPLY_CONFORMED_DIR, None)
    builder = BridgeBuilder(load_bridge(BRIDGE_SEMANTIC_DIR), load_catalog(PLANT_SEMANTIC_DIR), store)
    data = builder.build(args.seed)
    paths = write_bridge_tables(data.tables, data.manifest, BRIDGE_DATA_DIR)
    logger.info("Wrote %d files to %s", len(paths), BRIDGE_DATA_DIR)
    logger.info("Emergency buys: %s", data.manifest["emergency_buys"] or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
