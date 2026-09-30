"""Environment-driven settings for the copilot, each with an explicit default.

The copilot reads the plant and supply data where their own packages write it, and keeps its bridge data apart.
All environment reads for the copilot happen here, once, at import time.
"""
from __future__ import annotations

import os
from pathlib import Path

from pdm_oee.services.settings import CONFORMED_DIR as PLANT_CONFORMED_DIR
from pdm_oee.services.settings import SEMANTIC_DIR as PLANT_SEMANTIC_DIR
from supply_ontology.services.settings import CONFORMED_DIR as SUPPLY_CONFORMED_DIR

BRIDGE_DATA_DIR = Path(os.getenv("BRIDGE_DATA_DIR", "data/bridge"))
BRIDGE_SEMANTIC_DIR = Path(os.getenv("BRIDGE_SEMANTIC_DIR", "semantic/bridge"))
BRIDGE_SEED = int(os.getenv("BRIDGE_SEED", "20261018"))

__all__ = ["BRIDGE_DATA_DIR", "BRIDGE_SEED", "BRIDGE_SEMANTIC_DIR", "PLANT_CONFORMED_DIR", "PLANT_SEMANTIC_DIR",
           "SUPPLY_CONFORMED_DIR"]
