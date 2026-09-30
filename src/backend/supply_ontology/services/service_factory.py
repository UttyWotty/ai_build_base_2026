"""Builds the default services, loads the team recipes, and reads saved demo runs, so entry points never reach adapters directly.

Everything here uses services.settings for locations and the model endpoint.
Callers that need a different model or database pass their own objects to the service constructors instead.
"""
from __future__ import annotations

import json
from pathlib import Path

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.team_recipes import TeamRecipe, parse_recipes
from supply_ontology.data_pipeline.llm_client import LLMClient, build_llm_client
from supply_ontology.data_pipeline.raw_source_database import RawSourceDatabase
from supply_ontology.data_pipeline.semantic_files import (
    load_catalog,
    load_yaml_document,
)
from supply_ontology.services.settings import (
    DEMO_DIR,
    SEMANTIC_DIR,
    SOURCES_DIR,
)

__all__ = [
    "LLMClient", "default_llm_client", "default_raw_database", "load_default_catalog", "load_saved_demo_runs",
    "load_team_recipes",
]
RECIPES_FILE = Path("demo/supply/team_recipes.yaml")
SAVED_RUN_PATTERN = "*.json"
FILE_ENCODING = "utf-8"


def load_default_catalog() -> SemanticCatalog:
    """The validated catalog from the semantic directory."""
    return load_catalog(SEMANTIC_DIR)


def default_llm_client() -> LLMClient:
    """The client for the configured model (Gemini or local); nothing is sent until a question is asked."""
    return build_llm_client()


def load_team_recipes(catalog: SemanticCatalog, path: Path = RECIPES_FILE) -> tuple[TeamRecipe, ...]:
    """The illustrative team recipes, checked against the catalog's personas and metrics."""
    return parse_recipes(load_yaml_document(path), catalog.vocabulary.personas, catalog.metrics)


def default_raw_database() -> RawSourceDatabase:
    """The raw source exports under data/sources, locked for read-only queries."""
    return RawSourceDatabase.from_directory(SOURCES_DIR)


def load_saved_demo_runs(directory: Path = DEMO_DIR) -> dict[str, dict[str, object]]:
    """Saved consistency demo runs keyed by model name, newest file last; empty when none exist."""
    runs = {}
    for path in sorted(directory.glob(SAVED_RUN_PATTERN), key=lambda p: p.stat().st_mtime):
        report = json.loads(path.read_text(encoding=FILE_ENCODING))
        runs[str(report.get("model", path.stem))] = report
    return runs
