"""Every source trap has a round trip back to the truth; these tests are the specification for the conform step.

Units, tag paths, quality codes, local times with daylight saving, cumulative counters with resets,
mixed routing units, blank failure codes, and duplicate work orders are each resolved here by hand.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.data_pipeline.synthetic.reference import SITES
from pdm_oee.data_pipeline.synthetic.world import World

SITE = {s.site_id: s for s in SITES}


def frame(sources: dict, path: str) -> pd.DataFrame:
    return sources[path].frame


def to_utc(local: pd.Series, zone: str) -> pd.Series:
    return local.dt.tz_localize(zone, ambiguous="infer").dt.tz_convert("UTC").dt.tz_localize(None)


def test_historian_units_tags_and_quality_round_trip(small_world: World, small_sources: dict) -> None:
    tags = frame(small_sources, "asset_register/sensors.xlsx")
    assets = frame(small_sources, "asset_register/assets.xlsx")
    readings = frame(small_sources, "historian/readings.parquet").merge(tags, on="TAG").merge(assets[["ASSET_NO", "SITE"]], on="ASSET_NO")
    value = readings["VALUE"].astype(float)
    value = np.where(readings["ENG_UNIT"] == "degF", (value - 32) * 5 / 9, value)
    value = np.where(readings["ENG_UNIT"] == "psi", value / 14.5038, value)
    good = readings["QUALITY"].astype(str) == readings["SITE"].map(lambda s: str(SITE[s].good_quality))
    truth = small_world.tables["sensor_reading"]
    assert len(readings) == len(truth)
    assert np.allclose(np.sort(value), np.sort(truth["value"].to_numpy()), atol=0.01)
    assert int((~good).sum()) == int((truth["quality"] == "bad").sum())


def test_mes_states_resolve_to_utc_with_sequence_order(small_world: World, small_sources: dict) -> None:
    states = frame(small_sources, "mes/states.parquet")
    assets = small_world.tables["asset"].set_index("workcenter")
    rebuilt = []
    for workcenter, group in states.sort_values(["WORKCENTER", "SEQ"]).groupby("WORKCENTER"):
        zone = SITE[assets.loc[workcenter, "site_id"]].timezone
        rebuilt.append(pd.DataFrame({"asset_id": assets.loc[workcenter, "asset_id"],
                                     "start_at": to_utc(group["START_LOCAL"], zone).to_numpy()}))
    truth = small_world.tables["machine_state"].sort_values(["asset_id", "start_at"])
    assert (pd.concat(rebuilt).sort_values(["asset_id", "start_at"])["start_at"].to_numpy() == truth["start_at"].to_numpy()).all()


def test_mes_counters_resolve_to_shift_counts(small_world: World, small_sources: dict) -> None:
    counts = frame(small_sources, "mes/counts.parquet").sort_values(["WORKCENTER", "SHIFT_END_LOCAL"])
    previous = counts.groupby("WORKCENTER")["CUM_TOTAL"].shift()
    delta = np.where(counts["CUM_TOTAL"] < previous, counts["CUM_TOTAL"], counts["CUM_TOTAL"] - previous)
    baseline = previous.isna().to_numpy()
    assert (counts.loc[baseline, "ORDER_NO"] == "").all() and int(baseline.sum()) == len(small_world.tables["asset"])
    assert (counts["CUM_TOTAL"] < previous).any()
    truth = small_world.tables["production_count"].merge(small_world.tables["shift"][["shift_id", "end_at"]], on="shift_id")
    truth = truth.merge(small_world.tables["asset"][["asset_id", "workcenter"]], on="asset_id").sort_values(["workcenter", "end_at"])
    assert (delta[~baseline] == truth["total_count"].to_numpy()).all()


def test_routings_convert_to_seconds_per_part(small_world: World, small_sources: dict) -> None:
    us = frame(small_sources, "erp/routings_US1.xlsx")
    de = frame(small_sources, "erp/routings_DE1.xlsx")
    seconds = pd.concat([pd.Series((3600 / us["PARTS_PER_HOUR"]).round(1).to_numpy(), index=us["PRODUCT"] + "|" + us["EQUIPMENT_TYPE"]),
                         pd.Series(de["CYCLE_SECONDS"].to_numpy(), index=de["PRODUCT"] + "|" + de["EQUIPMENT_TYPE"])])
    assert len(seconds) == len(small_world.tables["routing"])
    assert set(seconds.round(1)) <= set(small_world.tables["routing"]["ideal_cycle_s"])


def test_cmms_noise_is_recoverable(small_world: World, small_sources: dict) -> None:
    orders = frame(small_sources, "cmms/work_orders.xlsx")
    truth = small_world.tables["work_order"]
    extra = orders[~orders["WO_NO"].isin(truth["wo_id"])]
    assert len(extra) == len(small_world.duplicates) > 0
    for row in extra.itertuples():
        earlier = orders[(orders["ASSET_NO"] == row.ASSET_NO) & (orders["TYPE"] == "CM")
                         & (orders["CREATED"] < row.CREATED) & (orders["CREATED"] >= row.CREATED - pd.Timedelta(hours=1))]
        assert len(earlier) >= 1
    blank = orders[(orders["TYPE"] == "CM") & (orders["FAILURE_CODE"] == "") & orders["WO_NO"].isin(truth["wo_id"])]
    assert set(blank["WO_NO"]) == set(small_world.missing_code_ids)
