"""Collects every source system rendering of the simulated plant into one list of source files.

The order is fixed so manifests and file listings are stable between runs.
Renderers are pure; the MES renderer draws its counter resets from its own named random stream.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.synthetic.random_streams import stream
from pdm_oee.data_pipeline.synthetic.render_cmms import render_cmms
from pdm_oee.data_pipeline.synthetic.render_erp import render_erp
from pdm_oee.data_pipeline.synthetic.render_historian import render_historian
from pdm_oee.data_pipeline.synthetic.render_mes import render_mes
from pdm_oee.data_pipeline.synthetic.render_register import render_register
from pdm_oee.data_pipeline.synthetic.source_file import SourceFile
from pdm_oee.data_pipeline.synthetic.world import World


def render_sources(world: World, catalog: PlantCatalog, seed: int) -> list[SourceFile]:
    """Asset register, historian, MES, ERP, and CMMS exports of the plant."""
    tables = world.tables
    return [
        *render_register(tables, catalog.plant),
        *render_historian(tables),
        *render_mes(tables, catalog.losses, pd.Timestamp(world.clock.start).tz_localize(None), stream(seed, "mes_counters")),
        *render_erp(tables, catalog.plant),
        *render_cmms(tables, world.missing_code_ids, world.duplicates),
    ]
