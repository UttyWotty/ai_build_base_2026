"""Environment-driven settings for the services and entry points, each with an explicit default.

All environment reads in the application layer happen here, once, at import time.
Paths are relative to the working directory, which is the repository root when run through make.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.getenv("SUPPLY_DATA_DIR", "data/supply"))
SEMANTIC_DIR = Path(os.getenv("SUPPLY_SEMANTIC_DIR", "semantic/supply"))
CONFORMED_DIR = DATA_DIR / "conformed"
SOURCES_DIR = DATA_DIR / "sources"
DEMO_DIR = DATA_DIR / "demo"
