"""Shared pytest fixtures: the governed catalog, and synthetic plants built once per test session.

The small plant covers 12 weeks with every story moved inside it; the full plant is the default year from docs/plan.md.
Tests treat both as read-only.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.data_pipeline.synthetic.config import (
    GenerationConfig,
    ScaleConfig,
    StoryConfig,
)
from pdm_oee.data_pipeline.synthetic.source_file import SourceFile
from pdm_oee.data_pipeline.synthetic.sources import render_sources
from pdm_oee.data_pipeline.synthetic.world import World, build_world

SEMANTIC_DIR = Path(__file__).resolve().parents[2] / "semantic" / "pdm"
SMALL_SEED = 7
SMALL_CONFIG = GenerationConfig(
    seed=SMALL_SEED,
    scale=ScaleConfig(weeks=12),
    stories=StoryConfig(bearing_failure_day=60, pump_failure_day=70, calibration_day=30),
)


@pytest.fixture(scope="session")
def catalog() -> PlantCatalog:
    return load_catalog(SEMANTIC_DIR)


@pytest.fixture(scope="session")
def small_world(catalog: PlantCatalog) -> World:
    return build_world(SMALL_CONFIG, catalog)


@pytest.fixture(scope="session")
def small_sources(small_world: World, catalog: PlantCatalog) -> dict[str, SourceFile]:
    return {s.relative_path: s for s in render_sources(small_world, catalog, SMALL_SEED)}


@pytest.fixture(scope="session")
def full_world(catalog: PlantCatalog) -> World:
    return build_world(GenerationConfig(), catalog)
