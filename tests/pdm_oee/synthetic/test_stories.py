"""The six planted stories are present in the data, measured from the tables rather than taken from the configuration.

Signal checks use running intervals only, since an idle machine does not vibrate.
Scrap and preventive-maintenance stories are checked on the full year; the rest on the small plant.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.data_pipeline.synthetic.world import World
from tests.pdm_oee.conftest import SMALL_CONFIG

STORIES = SMALL_CONFIG.stories
DAY = pd.Timedelta(days=1)


def running_readings(world: World, sensor_id: str) -> pd.Series:
    readings = world.tables["sensor_reading"]
    series = readings[(readings["sensor_id"] == sensor_id) & (readings["quality"] == "good")].set_index("ts")["value"]
    asset_id = sensor_id.split("/")[0]
    states = world.tables["machine_state"]
    running = states[(states["asset_id"] == asset_id) & (states["state"] == "running")]
    index = pd.IntervalIndex.from_arrays(running["start_at"], running["end_at"], closed="left")
    inside = index.get_indexer(series.index) >= 0
    return series[inside]


def first_day_above(series: pd.Series, limit: float) -> pd.Timestamp:
    return series[series > limit].index.min()


def test_bearing_warns_in_vibration_before_temperature(small_world: World) -> None:
    failed = pd.Timestamp(small_world.story_facts.bearing_failed_at)
    assert failed.normalize() == pd.Timestamp(small_world.clock.start).tz_localize(None) + STORIES.bearing_failure_day * DAY
    window = slice(failed - 7 * DAY, failed)
    vibration = running_readings(small_world, f"{STORIES.bearing_asset_id}/spindle_vibration")[window]
    temperature = running_readings(small_world, f"{STORIES.bearing_asset_id}/spindle_temperature")[window]
    first_vibration, first_temperature = first_day_above(vibration, 2.8), first_day_above(temperature, 55)
    assert failed - first_vibration > DAY
    assert first_temperature > first_vibration


def test_pump_wear_builds_over_three_weeks(small_world: World) -> None:
    failed = pd.Timestamp(small_world.story_facts.pump_failed_at)
    ripple = running_readings(small_world, f"{STORIES.pump_asset_id}/pressure_ripple")
    early = ripple[failed - 30 * DAY:failed - 22 * DAY].mean()
    late = ripple[failed - 3 * DAY:failed].mean()
    assert late > early + 2


def test_calibration_step_without_failure(small_world: World) -> None:
    sensor = small_world.story_facts.calibration_sensor_id
    swapped = pd.Timestamp(small_world.story_facts.calibration_at)
    series = running_readings(small_world, sensor)
    step = series[swapped:swapped + 14 * DAY].mean() - series[swapped - 14 * DAY:swapped].mean()
    assert abs(step - STORIES.calibration_offset) < 2.0
    failures = small_world.tables["failure_event"]
    near = failures[(failures["asset_id"] == STORIES.calibration_asset_id)
                    & (failures["failed_at"].between(swapped - 7 * DAY, swapped + 7 * DAY))
                    & (failures["failure_mode"] == "spindle_bearing_wear")]
    assert near.empty


def test_small_stops_concentrate_on_one_conveyor(small_world: World) -> None:
    facts = small_world.story_facts
    assert facts.small_stop_asset_stops_per_shift > 5 * facts.other_conveyor_stops_per_shift


def test_year_long_stories(full_world: World) -> None:
    facts = full_world.story_facts
    assert facts.over_maintained_pm_per_asset > 1.6 * facts.other_pm_per_asset
    assert facts.coolant_line_summer_scrap_share > 2 * facts.coolant_line_winter_scrap_share
    assert pd.Timestamp(facts.bearing_failed_at) > pd.Timestamp(full_world.clock.start).tz_localize(None) + 243 * DAY
