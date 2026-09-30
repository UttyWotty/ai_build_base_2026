"""Invariants of the simulated plant: determinism, complete state timelines, possible counts, and consistent failures.

Every check runs on the small plant, except where a full year is needed.
A failure here means the world itself is inconsistent, before any source rendering.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.synthetic.fingerprint import frame_fingerprint
from pdm_oee.data_pipeline.synthetic.sources import render_sources
from pdm_oee.data_pipeline.synthetic.world import World, build_world
from tests.pdm_oee.conftest import SMALL_CONFIG, SMALL_SEED


def test_same_seed_gives_identical_tables_and_sources(small_world: World, catalog: PlantCatalog, small_sources: dict) -> None:
    again = build_world(SMALL_CONFIG, catalog)
    assert {k: frame_fingerprint(v) for k, v in again.tables.items()} == {k: frame_fingerprint(v) for k, v in small_world.tables.items()}
    rendered = {s.relative_path: frame_fingerprint(s.frame) for s in render_sources(again, catalog, SMALL_SEED)}
    assert rendered == {path: frame_fingerprint(s.frame) for path, s in small_sources.items()}


def test_states_tile_every_asset_timeline_without_gaps(small_world: World) -> None:
    states = small_world.tables["machine_state"]
    start = pd.Timestamp(small_world.clock.start).tz_localize(None)
    end = start + pd.Timedelta(minutes=small_world.clock.minutes)
    for _, group in states.groupby("asset_id"):
        assert group["start_at"].iloc[0] == start and group["end_at"].iloc[-1] == end
        assert (group["start_at"].iloc[1:].to_numpy() == group["end_at"].iloc[:-1].to_numpy()).all()
        assert (group["reason"].iloc[1:].to_numpy() != group["reason"].iloc[:-1].to_numpy()).all()


def test_counts_are_physically_possible(small_world: World) -> None:
    tables = small_world.tables
    counts = tables["production_count"].merge(tables["asset"][["asset_id", "asset_class"]], on="asset_id")
    counts = counts.merge(tables["routing"], on=["product_id", "asset_class"]).merge(tables["shift"], on="shift_id")
    shift_seconds = (counts["end_at"] - counts["start_at"]).dt.total_seconds()
    assert (counts["total_count"] * counts["ideal_cycle_s"] <= shift_seconds).all()
    assert (counts["startup_scrap_count"] <= counts["scrap_count"]).all() and (counts["scrap_count"] <= counts["total_count"]).all()


def test_each_failure_is_one_breakdown_and_one_corrective_order(small_world: World, catalog: PlantCatalog) -> None:
    tables = small_world.tables
    failures, states = tables["failure_event"], tables["machine_state"]
    breakdowns = states[states["reason"] == "equipment_failure"]
    joined = failures.merge(breakdowns, left_on=["asset_id", "failed_at", "restored_at"],
                            right_on=["asset_id", "start_at", "end_at"])
    assert len(joined) == len(failures) == len(breakdowns)
    corrective = tables["work_order"][tables["work_order"]["work_type"] == "corrective"]
    assert set(corrective["wo_id"]) == set(failures["failure_id"])
    classes = tables["asset"].set_index("asset_id")["asset_class"]
    for failure in failures.itertuples():
        assert failure.failure_mode in catalog.plant.asset_classes[classes[failure.asset_id]].failure_modes


def test_bad_quality_marks_only_spikes(small_world: World, catalog: PlantCatalog) -> None:
    readings = small_world.tables["sensor_reading"].merge(small_world.tables["sensor"], on="sensor_id")
    readings = readings.merge(small_world.tables["asset"][["asset_id", "asset_class"]], on="asset_id")
    high = [catalog.plant.asset_classes[c].sensors[s].normal_range[1] for c, s in zip(readings["asset_class"], readings["sensor"])]
    bad = readings["quality"] == "bad"
    assert bad.any() and (readings.loc[bad, "value"] > pd.Series(high, index=readings.index)[bad] * 5).all()
    assert (readings.loc[~bad, "value"] < pd.Series(high, index=readings.index)[~bad] * 3).all()
