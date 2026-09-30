"""Historian readings: one value per sensor per sample interval, in canonical units, with a good or bad quality flag.

A value is the idle level plus the running share of the interval times the running level, plus wear symptoms (in the
failure mode's reaction order), the coolant season, a calibration offset after the story sensor swap, and noise.
Historian faults are part of the truth: missing intervals are absent, and spikes carry bad quality.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.plant_model import FailureMode, PlantModel, SensorSpec
from pdm_oee.data_pipeline.synthetic.calendar import Clock
from pdm_oee.data_pipeline.synthetic.config import StoryConfig
from pdm_oee.data_pipeline.synthetic.maintenance_plan import InstrumentWork
from pdm_oee.data_pipeline.synthetic.minute_states import RUNNING_CODE
from pdm_oee.data_pipeline.synthetic.reference import (
    ASSET_OFFSET_FRACTION,
    FALLING_SYMPTOMS,
    GAP_SHARE,
    IDLE_FRACTION,
    NOISE_FRACTION,
    OUTAGE_HOURS,
    OUTAGE_SENSOR_SHARE,
    SPIKE_FACTOR,
    SPIKE_SHARE,
    SYMPTOM_GAIN,
    SYMPTOM_LAG_SHARE,
    WEAR_EXPONENT,
)
from pdm_oee.data_pipeline.synthetic.reliability import Degradation
from pdm_oee.data_pipeline.synthetic.seasonal import coolant_rise

GOOD, BAD = "good", "bad"
COOLANT_SENSOR = "coolant_temperature"
MINUTES_PER_HOUR = 60


def symptom_start(mode: FailureMode, sensor: str, onset: int, failed: int) -> int:
    """When a symptom sensor starts to react: the first at onset, later ones spread over the first two thirds of P-F."""
    position, count = mode.symptoms.index(sensor), len(mode.symptoms)
    share = 0.0 if count == 1 else SYMPTOM_LAG_SHARE * position / (count - 1)
    return onset + int((failed - onset) * share)


def sensor_readings(sensors: pd.DataFrame, assets: pd.DataFrame, plant: PlantModel, minute_states: dict[str, np.ndarray],
                    degradations: list[Degradation], instruments: list[InstrumentWork], stories: StoryConfig,
                    clock: Clock, sample_minutes: int, rng: np.random.Generator) -> pd.DataFrame:
    """Every reading of every sensor over the horizon."""
    slots = clock.minutes // sample_minutes
    slot_minutes = np.arange(slots) * sample_minutes
    stamps = pd.date_range(clock.start, periods=slots, freq=f"{sample_minutes}min").tz_localize(None)
    day_of_year = stamps.dayofyear.to_numpy()
    classes = assets.set_index("asset_id")
    frames = []
    for sensor in sensors.itertuples():
        asset = classes.loc[sensor.asset_id]
        asset_class = plant.asset_classes[asset["asset_class"]]
        spec = asset_class.sensors[sensor.sensor]
        running = (minute_states[sensor.asset_id] == RUNNING_CODE).reshape(slots, sample_minutes).mean(axis=1)
        values = _level(spec, running, rng)
        values += _symptoms(sensor.asset_id, spec, asset_class.failure_modes, degradations, slot_minutes, running)
        if spec.id == COOLANT_SENSOR:
            values += coolant_rise(day_of_year, asset["line_id"] == stories.coolant_line_id, stories.coolant_summer_rise)
        for work in instruments:
            if (work.asset_id, work.sensor) == (sensor.asset_id, spec.id):
                values[slot_minutes >= work.minute] += work.offset
        frames.append(_with_faults(sensor.sensor_id, stamps, values, spec, sample_minutes, rng))
    return pd.concat(frames, ignore_index=True)


def _level(spec: SensorSpec, running: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    low, high = spec.normal_range
    mid, width = (low + high) / 2, high - low
    idle = low + IDLE_FRACTION[spec.sensor_type] * (mid - low)
    run = mid + rng.normal(0.0, ASSET_OFFSET_FRACTION * width)
    return idle + running * (run - idle) + rng.normal(0.0, NOISE_FRACTION * width, len(running))


def _symptoms(asset_id: str, spec: SensorSpec, modes: dict, degradations: list[Degradation],
              slot_minutes: np.ndarray, running: np.ndarray) -> np.ndarray:
    width = spec.normal_range[1] - spec.normal_range[0]
    effect = np.zeros(len(slot_minutes))
    for event in degradations:
        mode = modes.get(event.failure_mode)
        if event.asset_id != asset_id or mode is None or spec.id not in mode.symptoms or event.onset_minute is None:
            continue
        start = symptom_start(mode, spec.id, event.onset_minute, event.failed_minute)
        active = (slot_minutes >= start) & (slot_minutes < event.failed_minute)
        wear = ((slot_minutes[active] - start) / max(1, event.failed_minute - start)) ** WEAR_EXPONENT
        sign = -1.0 if (mode.id, spec.id) in FALLING_SYMPTOMS else 1.0
        effect[active] += sign * wear * width * SYMPTOM_GAIN * running[active]
    return effect


def _with_faults(sensor_id: str, stamps: pd.DatetimeIndex, values: np.ndarray, spec: SensorSpec,
                 sample_minutes: int, rng: np.random.Generator) -> pd.DataFrame:
    keep = rng.random(len(values)) >= GAP_SHARE
    if rng.random() < OUTAGE_SENSOR_SHARE:
        length = int(rng.uniform(*OUTAGE_HOURS) * MINUTES_PER_HOUR / sample_minutes)
        begin = int(rng.integers(0, max(1, len(values) - length)))
        keep[begin:begin + length] = False
    spikes = rng.random(len(values)) < SPIKE_SHARE
    values = np.where(spikes, spec.normal_range[1] * SPIKE_FACTOR, values)
    return pd.DataFrame({"sensor_id": sensor_id, "ts": stamps[keep], "value": np.round(values[keep], 3),
                         "quality": np.where(spikes[keep], BAD, GOOD)})
