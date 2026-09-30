"""Renders the historian export: readings keyed by tag path, in each site's engineering units, with site quality codes.

US1 prints temperatures in degrees Fahrenheit and pressures in psi, and OPC numeric quality as text ("192" good, "0" bad);
DE1 prints metric units and "Good" or "Bad". Timestamps stay in UTC, as historians store them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.synthetic.reference import SITES
from pdm_oee.data_pipeline.synthetic.render_register import tag_path
from pdm_oee.data_pipeline.synthetic.sensors import GOOD
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile

FAHRENHEIT_SCALE, FAHRENHEIT_OFFSET = 9.0 / 5.0, 32.0
PSI_PER_BAR = 14.5038
VALUE_DECIMALS = 3


def render_historian(tables: dict[str, pd.DataFrame]) -> list[SourceFile]:
    sensors = tables["sensor"].merge(tables["asset"], on="asset_id").merge(tables["line"][["line_id", "line_number"]], on="line_id")
    sensors["tag"] = [tag_path(s, n, c, x) for s, n, c, x in
                      zip(sensors["site_id"], sensors["line_number"], sensors["tag_code"], sensors["sensor"])]
    info = sensors.set_index("sensor_id")
    readings = tables["sensor_reading"]
    site = readings["sensor_id"].map(info["site_id"])
    unit = readings["sensor_id"].map(info["unit"])
    imperial = site.map({s.site_id: s.imperial_units for s in SITES}).astype(bool)
    value = readings["value"].to_numpy(dtype=float).copy()
    hot = (imperial & (unit == "deg_c")).to_numpy()
    value[hot] = value[hot] * FAHRENHEIT_SCALE + FAHRENHEIT_OFFSET
    pressed = (imperial & (unit == "bar")).to_numpy()
    value[pressed] = value[pressed] * PSI_PER_BAR
    good = {s.site_id: str(s.good_quality) for s in SITES}
    bad = {s.site_id: str(s.bad_quality) for s in SITES}
    quality = np.where(readings["quality"] == GOOD, site.map(good), site.map(bad))
    frame = pd.DataFrame({"TAG": readings["sensor_id"].map(info["tag"]).astype("category"), "TIMESTAMP_UTC": readings["ts"],
                          "VALUE": np.round(value, VALUE_DECIMALS), "QUALITY": pd.Categorical(quality)})
    return [SourceFile("historian/readings.parquet", frame, FileFormat.PARQUET)]
