"""Master data for the plant: sites, lines, assets, components, sensors, products, and ideal cycle times.

Assets, components, and sensors follow the governed plant model; the layout and products follow reference.py.
Every id here is canonical; the renderers derive the source systems' own numbers and names from it.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pdm_oee.core.plant_model import PlantModel
from pdm_oee.data_pipeline.synthetic.config import ScaleConfig
from pdm_oee.data_pipeline.synthetic.reference import (
    BASE_CYCLE_SECONDS,
    CRITICALITY,
    FAMILIES,
    LINE_LAYOUT,
    NAMEPLATE_FACTOR,
    PRODUCT_PREFIX,
    PRODUCT_VARIANTS,
    SITES,
)

SENSOR_ID_SEPARATOR = "/"


@dataclass(frozen=True)
class Masters:
    """All master tables, keyed by canonical ids."""

    sites: pd.DataFrame
    lines: pd.DataFrame
    assets: pd.DataFrame
    components: pd.DataFrame
    sensors: pd.DataFrame
    products: pd.DataFrame
    routings: pd.DataFrame


def sensor_id(asset_id: str, sensor: str) -> str:
    """Canonical sensor id: the asset id and the sensor position."""
    return f"{asset_id}{SENSOR_ID_SEPARATOR}{sensor}"


def build_masters(plant: PlantModel, scale: ScaleConfig) -> Masters:
    """Sites, lines, assets and their parts, and products for every line."""
    sites = pd.DataFrame([{"site_id": s.site_id, "timezone": s.timezone, "imperial_units": s.imperial_units} for s in SITES])
    lines, assets = [], []
    for site in SITES:
        for number in range(1, scale.lines_per_site + 1):
            line_id = f"{site.site_id}-L{number}"
            family = FAMILIES[site.site_id][(number - 1) % len(FAMILIES[site.site_id])]
            lines.append({"line_id": line_id, "site_id": site.site_id, "line_number": number, "family": family})
            assets += [_asset(site.site_id, site.number, line_id, number, position, asset_class, code)
                       for position, asset_class, code in LINE_LAYOUT]
    products, routings = _products(pd.DataFrame(lines))
    assets_frame = pd.DataFrame(assets)
    fastest = min(factor for _, factor in PRODUCT_VARIANTS)
    assets_frame["nameplate_cycle_s"] = [round(BASE_CYCLE_SECONDS[c] * fastest * NAMEPLATE_FACTOR, 1)
                                         for c in assets_frame["asset_class"]]
    return Masters(sites, pd.DataFrame(lines), assets_frame, *_parts(assets_frame, plant), products, routings)


def _asset(site_id: str, site_number: int, line_id: str, line: int, position: int, asset_class: str, code: str) -> dict:
    return {"asset_id": f"{line_id}-{position:02d}", "line_id": line_id, "site_id": site_id, "asset_class": asset_class,
            "position": position, "criticality": CRITICALITY[asset_class], "tag_code": code,
            "asset_number": f"{site_number}{line:02d}{position:02d}", "workcenter": f"WC-{site_id}-{line:02d}{position:02d}"}


def _products(lines: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    products, routings = [], []
    for family in lines["family"].unique():
        for variant, factor in PRODUCT_VARIANTS:
            product_id = f"{PRODUCT_PREFIX[family]}-{variant}"
            products.append({"product_id": product_id, "family": family})
            routings += [{"product_id": product_id, "asset_class": c, "ideal_cycle_s": round(base * factor, 1)}
                         for c, base in BASE_CYCLE_SECONDS.items()]
    return pd.DataFrame(products), pd.DataFrame(routings)


def _parts(assets: pd.DataFrame, plant: PlantModel) -> tuple[pd.DataFrame, pd.DataFrame]:
    components, sensors = [], []
    for asset in assets.itertuples():
        spec = plant.asset_classes[asset.asset_class]
        components += [{"asset_id": asset.asset_id, "component": c} for c in spec.components]
        sensors += [{"sensor_id": sensor_id(asset.asset_id, s.id), "asset_id": asset.asset_id, "sensor": s.id,
                     "sensor_type": s.sensor_type, "component": s.component,
                     "unit": plant.sensor_types[s.sensor_type].unit.value} for s in spec.sensors.values()]
    return pd.DataFrame(components), pd.DataFrame(sensors)
