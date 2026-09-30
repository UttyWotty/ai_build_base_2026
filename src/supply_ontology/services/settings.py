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
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-6Bit")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
