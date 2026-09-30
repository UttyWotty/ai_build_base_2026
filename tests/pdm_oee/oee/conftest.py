"""Makes the conform fixtures (mappings, rendered sources, conformed tables) available to the OEE tests.

The conformed small plant is built once per session by the conform fixtures.
Nothing here changes the fixtures.
"""
from __future__ import annotations

from tests.pdm_oee.conform.conftest import conformed, mappings, source_frames

__all__ = ["conformed", "mappings", "source_frames"]
