"""Shared pytest fixtures: one small synthetic world, built once per test session.

The small config keeps every planted story detectable while generating in about a second.
Tests treat the world as read-only; any test that needs to mutate data copies a frame first.
"""
from __future__ import annotations

import pytest

from supply_ontology.data_pipeline.synthetic.config import (
    GenerationConfig,
    ScaleConfig,
    StoryConfig,
)
from supply_ontology.data_pipeline.synthetic.world import World, build_world

SMALL_SEED = 7
SMALL_CONFIG = GenerationConfig(
    seed=SMALL_SEED,
    scale=ScaleConfig(supplier_count=12, part_count=80, customer_count=30, weeks=52, sales_lines_per_week=160),
    stories=StoryConfig(degradation_start_week=26, degradation_weeks=8, freight_spike_start_week=20, freight_spike_weeks=13),
)


@pytest.fixture(scope="session")
def small_world() -> World:
    """The small world shared by all synthetic tests."""
    return build_world(SMALL_CONFIG)
