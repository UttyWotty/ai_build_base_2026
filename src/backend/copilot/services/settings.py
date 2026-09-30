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
# Where the agent's action proposals wait for approval.
PROPOSALS_PATH = Path(os.getenv("PROPOSALS_PATH", "data/copilot/proposals.json"))
# The demo clock: the moment the copilot treats as now. The planted bearing alert was raised at this time.
DEMO_AS_OF = os.getenv("DEMO_AS_OF", "2026-07-25T02:00")
# Field inputs Gemini has read, and the sample photos and supplier messages for the demo.
INSPECTIONS_PATH = Path(os.getenv("INSPECTIONS_PATH", "data/copilot/inspections.json"))
SUPPLIER_UPDATES_PATH = Path(os.getenv("SUPPLIER_UPDATES_PATH", "data/copilot/supplier_updates.json"))
FIELD_SAMPLES_DIR = Path(os.getenv("FIELD_SAMPLES_DIR", "demo/field"))
# The built React app; absent during local development, where Vite serves it.
FRONTEND_DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", "src/frontend/dist"))

__all__ = ["BRIDGE_DATA_DIR", "BRIDGE_SEED", "BRIDGE_SEMANTIC_DIR", "DEMO_AS_OF", "FIELD_SAMPLES_DIR", "FRONTEND_DIST_DIR",
           "INSPECTIONS_PATH", "SUPPLIER_UPDATES_PATH", "PROPOSALS_PATH", "PLANT_CONFORMED_DIR", "PLANT_SEMANTIC_DIR",
           "SUPPLY_CONFORMED_DIR"]
