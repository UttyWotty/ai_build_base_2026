"""Determinism tests: the same config must produce identical content, and a different seed must not.

Fingerprints cover every truth table and every rendered source frame.
The small config is rebuilt here on purpose, rather than reusing the session fixture, to prove repeatability.
"""
from __future__ import annotations

from dataclasses import replace

from supply_ontology.data_pipeline.synthetic.fingerprint import frame_fingerprint
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World, build_world
from tests.supply_ontology.conftest import SMALL_CONFIG


def _fingerprints(world: World) -> dict[str, str]:
    prints = {name: frame_fingerprint(frame) for name, frame in world.tables.items()}
    prints.update({s.relative_path: frame_fingerprint(s.frame) for s in render_sources(world)})
    return prints


def test_same_seed_reproduces_every_table_and_source(small_world: World) -> None:
    assert _fingerprints(build_world(SMALL_CONFIG)) == _fingerprints(small_world)


def test_different_seed_changes_the_data(small_world: World) -> None:
    other = _fingerprints(build_world(replace(SMALL_CONFIG, seed=SMALL_CONFIG.seed + 1)))
    assert other["sales_order_line"] != _fingerprints(small_world)["sales_order_line"]
