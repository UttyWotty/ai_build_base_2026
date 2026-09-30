"""The conform pipeline must fail loudly, never silently drop or null out data it cannot map.

Each test corrupts one aspect of otherwise valid rendered sources and expects ConformError with a useful message.
Date helpers are covered here as well because their failure modes are the same class of trap.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.dates import (
    day_first_dates,
    utc_to_local_dates,
)
from supply_ontology.data_pipeline.conform.errors import ConformError
from supply_ontology.data_pipeline.conform.pipeline import conform_sources
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World
from tests.supply_ontology.conform.test_conform_matches_truth import (
    SEMANTIC_DIR,
    TRAILING_WINDOW_DAYS,
)

ONTOLOGY = load_catalog(SEMANTIC_DIR).ontology


def _sources(world: World) -> dict[str, pd.DataFrame]:
    return {s.relative_path: s.frame.copy() for s in render_sources(world)}


def test_missing_file_is_reported(small_world: World) -> None:
    sources = _sources(small_world)
    del sources[layout.MDM_CROSSWALK]
    with pytest.raises(ConformError, match="missing file mdm/partner_crosswalk.xlsx"):
        conform_sources(sources, ONTOLOGY, TRAILING_WINDOW_DAYS)


def test_unmapped_partner_code_is_reported(small_world: World) -> None:
    sources = _sources(small_world)
    sources[layout.MDM_CROSSWALK] = sources[layout.MDM_CROSSWALK].iloc[1:]
    with pytest.raises(ConformError, match="unmapped value"):
        conform_sources(sources, ONTOLOGY, TRAILING_WINDOW_DAYS)


def test_unknown_status_code_is_reported(small_world: World) -> None:
    sources = _sources(small_world)
    sources[layout.ERP_SO_ITEMS].loc[0, "STATUS"] = "Z"
    with pytest.raises(ConformError, match="sales order line status code"):
        conform_sources(sources, ONTOLOGY, TRAILING_WINDOW_DAYS)


def test_unknown_unit_of_measure_is_reported(small_world: World) -> None:
    sources = _sources(small_world)
    sources[layout.TMS_OUTBOUND_LINES].loc[0, "UOM"] = "PAL"
    with pytest.raises(ConformError, match="Unknown TMS units"):
        conform_sources(sources, ONTOLOGY, TRAILING_WINDOW_DAYS)


def test_duplicate_crosswalk_code_is_reported(small_world: World) -> None:
    sources = _sources(small_world)
    crosswalk = sources[layout.MDM_CROSSWALK]
    sources[layout.MDM_CROSSWALK] = pd.concat([crosswalk, crosswalk.iloc[[0]]], ignore_index=True)
    with pytest.raises(ConformError, match="more than once"):
        conform_sources(sources, ONTOLOGY, TRAILING_WINDOW_DAYS)


def test_utc_timestamps_become_local_dates() -> None:
    utc = pd.Series(["2025-03-04T22:00:00Z", "2025-03-04T22:00:00Z", None])
    zones = pd.Series(["Asia/Shanghai", "America/Chicago", "Asia/Shanghai"])
    assert utc_to_local_dates(utc, zones).tolist() == [date(2025, 3, 5), date(2025, 3, 4), None]


def test_day_first_text_dates() -> None:
    assert day_first_dates(pd.Series(["03/04/2025"])).tolist() == [date(2025, 4, 3)]
