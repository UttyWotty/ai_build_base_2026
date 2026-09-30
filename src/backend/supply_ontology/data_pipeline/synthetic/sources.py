"""Collects every simulated source system rendering of a world into one list of source files.

The order is fixed so manifests and file listings are stable between runs.
Each renderer is pure, so this module is pure as well.
"""
from __future__ import annotations

from supply_ontology.data_pipeline.synthetic.render_erp import render_erp
from supply_ontology.data_pipeline.synthetic.render_portal import render_portal
from supply_ontology.data_pipeline.synthetic.render_reference import render_reference
from supply_ontology.data_pipeline.synthetic.render_tms import render_tms
from supply_ontology.data_pipeline.synthetic.source_file import SourceFile
from supply_ontology.data_pipeline.synthetic.world import World


def render_sources(world: World) -> list[SourceFile]:
    """Render ERP, TMS, supplier portal, and reference files for the world."""
    return [
        *render_erp(world.tables, world.extras),
        *render_tms(world.tables, world.extras),
        *render_portal(world.tables, world.extras),
        *render_reference(world.extras),
    ]
