"""Conforms historian readings: tag paths to sensor ids, printed units to canonical units, site quality codes to good or bad.

Conversion follows the governed printed-unit table: canonical = (printed + offset) x scale, rounded to VALUE_DECIMALS.
A tag missing from the register, or a quality code the site does not declare, fails the conform step.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.source_layout import HISTORIAN, Sources

VALUE_DECIMALS = 3
GOOD, BAD = "good", "bad"


def conform_readings(sources: Sources, sensors: pd.DataFrame, assets: pd.DataFrame, mappings: SourceMappings) -> pd.DataFrame:
    readings = sources[HISTORIAN]
    info = sensors.merge(assets[["asset_id", "site_id"]], on="asset_id").set_index("tag")
    tags = readings["TAG"].astype(str)
    unknown = sorted(set(tags.unique()) - set(info.index))
    if unknown:
        raise ConformError(f"{HISTORIAN}: tags missing from the asset register {unknown[:5]}")
    printed = tags.map(info["eng_unit"])
    offset = printed.map({t: u.offset for t, u in mappings.printed_units.items()}).to_numpy(dtype=float)
    scale = printed.map({t: u.scale for t, u in mappings.printed_units.items()}).to_numpy(dtype=float)
    value = np.round((readings["VALUE"].to_numpy(dtype=float) + offset) * scale, VALUE_DECIMALS)
    return pd.DataFrame({"sensor_id": tags.map(info["sensor_id"]).to_numpy(), "ts": readings["TIMESTAMP_UTC"].to_numpy(),
                         "value": value, "quality": _quality(readings["QUALITY"].astype(str), tags.map(info["site_id"]), mappings)})


def _quality(codes: pd.Series, sites: pd.Series, mappings: SourceMappings) -> np.ndarray:
    lookup = {(s.site_id, c): GOOD for s in mappings.sites.values() for c in s.good_quality}
    lookup |= {(s.site_id, c): BAD for s in mappings.sites.values() for c in s.bad_quality}
    pairs = pd.Series(list(zip(sites, codes)), index=codes.index)
    distinct = set(pairs.unique())
    unknown = sorted(p for p in distinct if p not in lookup)
    if unknown:
        raise ConformError(f"{HISTORIAN}: undeclared quality codes {unknown}")
    return pairs.map(lookup).to_numpy()
