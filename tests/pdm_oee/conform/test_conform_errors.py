"""The conform step refuses data the governed mappings do not explain, naming what it found.

Each test copies the small plant's sources, breaks one thing, and expects a ConformError with a precise message.
Nothing is silently dropped, nulled, or guessed.
"""
from __future__ import annotations

import pandas as pd
import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.pipeline import conform_sources


def broken(frames: dict, path: str, change) -> dict:
    copy = dict(frames)
    copy[path] = change(frames[path].copy())
    return copy


def set_first(column: str, value: object):
    def change(frame: pd.DataFrame) -> pd.DataFrame:
        frame.loc[frame.index[0], column] = value
        return frame
    return change


@pytest.mark.parametrize("path, change, message", [
    ("historian/readings.parquet", lambda f: f.assign(TAG=f["TAG"].astype(str).where(f.index > 0, "US1.L9.CNC01.SPDL_VIB")),
     "tags missing from the asset register"),
    ("historian/readings.parquet", lambda f: f.assign(QUALITY=f["QUALITY"].astype(str).where(f.index > 0, "maybe")),
     "undeclared quality codes"),
    ("mes/states.parquet", set_first("REASON", "ZZZ"), "unknown reason code 'ZZZ'"),
    ("mes/states.parquet", set_first("STATE", "PAUSE"), "unknown state codes"),
    ("asset_register/assets.xlsx", set_first("ASSET_NO", "19901"), "does not follow site-line-position"),
    ("asset_register/sensors.xlsx", set_first("ENG_UNIT", "kelvin"), "does not convert"),
    ("mes/counts.parquet", lambda f: f.drop(index=f.index[0]).reset_index(drop=True), "go-live snapshot"),
])
def test_undeclared_data_fails_loudly(source_frames: dict, catalog: PlantCatalog, mappings: SourceMappings,
                                      path: str, change, message: str) -> None:
    with pytest.raises(ConformError, match=message):
        conform_sources(broken(source_frames, path, change), catalog, mappings)


def test_blank_failure_code_without_a_keyword_fails(source_frames: dict, catalog: PlantCatalog, mappings: SourceMappings) -> None:
    def change(frame: pd.DataFrame) -> pd.DataFrame:
        first = frame.index[(frame["TYPE"] == "CM") & frame["FAILURE_CODE"].notna()][0]
        frame.loc[first, ["FAILURE_CODE", "DESCRIPTION"]] = [None, "Something broke"]
        return frame
    with pytest.raises(ConformError, match="has no failure code and its text matches"):
        conform_sources(broken(source_frames, "cmms/work_orders.xlsx", change), catalog, mappings)


def test_missing_file_is_reported(source_frames: dict, catalog: PlantCatalog, mappings: SourceMappings) -> None:
    frames = {k: v for k, v in source_frames.items() if k != "mes/shift_calendar.xlsx"}
    with pytest.raises(ConformError, match="missing file mes/shift_calendar.xlsx"):
        conform_sources(frames, catalog, mappings)
