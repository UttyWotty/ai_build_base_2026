"""Renders the asset register: assets with their site numbers and names, and sensors with their historian tag paths.

The register is the only bridge between the MES workcenters, the CMMS asset numbers, and the historian tags.
Sensors are named by their measurement label and engineering unit as printed at each site.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.plant_model import PlantModel
from pdm_oee.data_pipeline.synthetic.reference import SENSOR_CODES, SITES
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile

IMPERIAL_UNITS = {"deg_c": "degF", "bar": "psi"}
PRINTED_UNITS = {"deg_c": "degC", "bar": "bar", "mm_per_s": "mm/s", "rpm": "rpm", "ampere": "A"}


def tag_path(site_id: str, line_number: int, tag_code: str, sensor: str) -> str:
    """Historian tag such as US1.L2.CNC01.SPDL_VIB."""
    return f"{site_id}.L{line_number}.{tag_code}.{SENSOR_CODES[sensor]}"


def render_register(tables: dict[str, pd.DataFrame], plant: PlantModel) -> list[SourceFile]:
    assets = tables["asset"].merge(tables["line"][["line_id", "line_number"]], on="line_id")
    imperial = {site.site_id: site.imperial_units for site in SITES}
    register = pd.DataFrame({
        "ASSET_NO": assets["asset_number"], "ASSET_NAME": [
            f"{plant.asset_classes[c].label} {p} Line {n}" for c, p, n in zip(assets["asset_class"], assets["position"], assets["line_number"])],
        "SITE": assets["site_id"], "LINE": assets["line_number"],
        "EQUIPMENT_TYPE": [plant.asset_classes[c].label for c in assets["asset_class"]],
        "CRITICALITY": assets["criticality"], "WORKCENTER": assets["workcenter"],
        "NAMEPLATE_CYCLE_S": assets["nameplate_cycle_s"],
    })
    sensors = tables["sensor"].merge(assets, on="asset_id")
    labels = [plant.asset_classes[c].sensors[s].label for c, s in zip(sensors["asset_class"], sensors["sensor"])]
    units = [IMPERIAL_UNITS.get(u, PRINTED_UNITS[u]) if imperial[site] else PRINTED_UNITS[u]
             for u, site in zip(sensors["unit"], sensors["site_id"])]
    tags = pd.DataFrame({
        "TAG": [tag_path(s, n, c, x) for s, n, c, x in zip(sensors["site_id"], sensors["line_number"], sensors["tag_code"], sensors["sensor"])],
        "ASSET_NO": sensors["asset_number"], "MEASUREMENT": labels, "ENG_UNIT": units,
    })
    return [SourceFile("asset_register/assets.xlsx", register, FileFormat.XLSX),
            SourceFile("asset_register/sensors.xlsx", tags, FileFormat.XLSX)]
