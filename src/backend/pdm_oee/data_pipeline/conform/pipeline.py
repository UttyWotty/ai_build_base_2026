"""Runs the whole conform step: checks the source layout, then builds every canonical table in dependency order.

The input is the source frames keyed by relative path, so tests can pass rendered frames without touching files.
The output is one frame per canonical entity, with the same columns the truth tables have.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.counts import conform_counts
from pdm_oee.data_pipeline.conform.maintenance import conform_maintenance
from pdm_oee.data_pipeline.conform.masters import (
    conform_assets,
    conform_components,
    conform_lines,
    conform_products,
    conform_routings,
    conform_sensors,
    conform_sites,
)
from pdm_oee.data_pipeline.conform.readings import conform_readings
from pdm_oee.data_pipeline.conform.schedule import conform_orders, conform_shifts
from pdm_oee.data_pipeline.conform.source_layout import Sources, check_sources
from pdm_oee.data_pipeline.conform.states import conform_states

SENSOR_COLUMNS = ["sensor_id", "asset_id", "sensor", "sensor_type", "component", "unit"]
# Canonical entities and the columns that identify one row of each.
ENTITY_KEYS: dict[str, tuple[str, ...]] = {
    "site": ("site_id",), "line": ("line_id",), "asset": ("asset_id",), "component": ("asset_id", "component"),
    "sensor": ("sensor_id",), "product": ("product_id",), "routing": ("product_id", "asset_class"),
    "shift": ("shift_id",), "production_order": ("order_id",), "machine_state": ("asset_id", "start_at"),
    "production_count": ("asset_id", "shift_id"), "sensor_reading": ("sensor_id", "ts"), "work_order": ("wo_id",),
    "failure_event": ("failure_id",),
}
ENTITIES = tuple(ENTITY_KEYS)


def conform_sources(sources: Sources, catalog: PlantCatalog, mappings: SourceMappings) -> dict[str, pd.DataFrame]:
    """Every canonical table, built from the source exports."""
    check_sources(sources)
    assets = conform_assets(sources, catalog, mappings)
    sensors = conform_sensors(sources, assets, catalog, mappings)
    products = conform_products(sources)
    orders = conform_orders(sources, mappings)
    states = conform_states(sources, assets, mappings)
    work_orders, failures = conform_maintenance(sources, assets, states, catalog, mappings)
    return {
        "site": conform_sites(sensors, assets, mappings),
        "line": conform_lines(sources, assets, products),
        "asset": assets,
        "component": conform_components(assets, catalog),
        "sensor": sensors[SENSOR_COLUMNS],
        "product": products,
        "routing": conform_routings(sources, catalog),
        "shift": conform_shifts(sources, mappings),
        "production_order": orders,
        "machine_state": states,
        "production_count": conform_counts(sources, assets, orders),
        "sensor_reading": conform_readings(sources, sensors, assets, mappings),
        "work_order": work_orders,
        "failure_event": failures,
    }
