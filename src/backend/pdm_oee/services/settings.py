"""Environment-driven settings for the services and entry points, each with an explicit default.

All environment reads in the application layer happen here, once, at import time.
Paths are relative to the working directory, which is the repository root when run through make.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.getenv("PDM_DATA_DIR", "data/pdm"))
SEMANTIC_DIR = Path(os.getenv("PDM_SEMANTIC_DIR", "semantic/pdm"))
CONFORMED_DIR = DATA_DIR / "conformed"
MODEL_DIR = DATA_DIR / "models"
OUTBOX_PATH = DATA_DIR / "outbox" / "work_order_drafts.json"
REPLAY_PATH = DATA_DIR / "alerts" / "replay.json"
