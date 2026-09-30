"""Shared catalog fixture for natural-language tests.

The catalog is loaded once from the checked-in semantic directory.
Tests treat it as read-only.
"""
from __future__ import annotations

from pathlib import Path

from supply_ontology.data_pipeline.semantic_files import load_catalog

CATALOG = load_catalog(Path(__file__).resolve().parents[3] / "semantic" / "supply")
