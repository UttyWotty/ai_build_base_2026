"""Golden OEE values on the hand-built plant, each derived by hand below.

A1 in S1: calendar 480, break 30 -> planned 450; long stops 60 + 40 + 10 + 30 (the breakdown's S1 part) = 140 -> run 310;
small stops 3 x 2 = 6 -> run net of all stops 304; ideal run 100 x 2 = 200; valuable 95 x 2 = 190; nameplate 95 x 100/60.
Waterfall: 450 - 90 - 40 - 10 - 6 - (310 - 6 - 200 = 104) - 4 - 6 = 190. A2 in S1: planned 480, run 480, ideal 400.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.loss_waterfall import loss_minutes, waterfall
from pdm_oee.core.metric_rollup import rollup
from pdm_oee.core.shift_measures import shift_measures, split_by_shift
from tests.pdm_oee.oee.golden_plant import tables


@pytest.fixture(scope="module")
def golden(catalog: PlantCatalog):
    t = tables()
    measures = shift_measures(t["machine_state"], t["shift"], t["asset"], t["production_count"], t["routing"], catalog)
    pieces = split_by_shift(t["machine_state"], t["shift"], t["asset"])
    return measures.set_index(["asset_id", "shift_id"]), loss_minutes(pieces, measures, catalog).set_index(["asset_id", "shift_id"]), measures


def test_asset_shift_measures(golden) -> None:
    measures, _, _ = golden
    a1 = measures.loc[("A1", "S1")]
    assert (a1["calendar_time"], a1["planned_production_time"], a1["run_time"], a1["run_time_all_stops"]) == (480, 450, 310, 304)
    assert (a1["ideal_run_time"], a1["valuable_operating_time"], a1["good_count"]) == (200, 190, 95)
    assert a1["nameplate_valuable_time"] == pytest.approx(95 * 100 / 60)
    s2 = measures.loc[("A1", "S2")]
    assert (s2["planned_production_time"], s2["run_time"], s2["ideal_run_time"]) == (480, 450, 400)


def test_metrics_multiply_and_roll_up_as_sums(golden, catalog: PlantCatalog) -> None:
    _, _, frame = golden
    per_row = rollup(frame, catalog, ["availability", "performance", "quality", "oee"], ["asset_id", "shift_id"]).set_index(["asset_id", "shift_id"])
    a1 = per_row.loc[("A1", "S1")]
    assert a1["availability"] == pytest.approx(310 / 450) and a1["performance"] == pytest.approx(200 / 310)
    assert a1["quality"] == pytest.approx(0.95) and a1["oee"] == pytest.approx(190 / 450)
    assert a1["oee"] == pytest.approx(a1["availability"] * a1["performance"] * a1["quality"])
    first_shift = rollup(frame[frame["shift_id"] == "S1"], catalog, ["oee"], [])
    assert first_shift["oee"].iloc[0] == pytest.approx((190 + 400) / (450 + 480))


def test_loss_waterfall_by_hand(golden, catalog: PlantCatalog) -> None:
    measures, losses, frame = golden
    a1 = losses.loc[("A1", "S1")]
    expected = {"breakdowns": 90, "setup_and_adjustments": 40, "external_stops": 10, "small_stops": 6,
                "reduced_speed": 104, "startup_rejects": 4, "production_rejects": 6}
    assert {k: round(a1[k], 6) for k in expected} == expected
    steps = waterfall(frame[frame["asset_id"] == "A1"], losses.reset_index()[losses.reset_index()["asset_id"] == "A1"], catalog)
    assert steps["minutes"].iloc[:-1].sum() == pytest.approx(steps["minutes"].iloc[-1])


def test_stop_crossing_a_shift_boundary_is_long_in_both_shifts(golden) -> None:
    _, losses, _ = golden
    assert losses.loc[("A1", "S2"), "breakdowns"] == 30 and losses.loc[("A1", "S2"), "small_stops"] == 0


def test_zero_denominator_has_no_value(golden, catalog: PlantCatalog) -> None:
    _, _, frame = golden
    empty = frame.assign(total_count=0, good_count=0)
    assert rollup(empty, catalog, ["quality"], []).isna().all().all()
