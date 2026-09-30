"""Builds the whole synthetic plant: master data, shifts, orders, failures, maintenance, states, counts, and readings.

The result holds the canonical truth tables (UTC timestamps, governed ids and reasons), the extras the renderers need
for source-only noise, and the story facts recorded in the manifest. Each step draws from its own named random stream.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.synthetic.calendar import Clock, make_clock, shift_table
from pdm_oee.data_pipeline.synthetic.config import GenerationConfig
from pdm_oee.data_pipeline.synthetic.machine_states import state_intervals
from pdm_oee.data_pipeline.synthetic.maintenance_plan import (
    plan_instrument_work,
    plan_preventive,
)
from pdm_oee.data_pipeline.synthetic.masters import build_masters
from pdm_oee.data_pipeline.synthetic.minute_states import (
    build_minute_states,
    state_codes,
)
from pdm_oee.data_pipeline.synthetic.orders import plan_orders
from pdm_oee.data_pipeline.synthetic.production import shift_counts
from pdm_oee.data_pipeline.synthetic.random_streams import stream
from pdm_oee.data_pipeline.synthetic.reference import BREAK_MINUTES, SITES
from pdm_oee.data_pipeline.synthetic.reliability import failure_frame, simulate_failures
from pdm_oee.data_pipeline.synthetic.sensors import sensor_readings
from pdm_oee.data_pipeline.synthetic.story_facts import StoryFacts, story_facts
from pdm_oee.data_pipeline.synthetic.work_orders import build_maintenance


@dataclass(frozen=True)
class World:
    """The simulated plant: truth tables, renderer extras, and story facts."""

    clock: Clock
    tables: dict[str, pd.DataFrame]
    missing_code_ids: frozenset[str]
    duplicates: pd.DataFrame
    story_facts: StoryFacts


def build_world(config: GenerationConfig, catalog: PlantCatalog) -> World:
    """Simulate the plant described by the configuration and the governed catalog."""
    plant, stories, seed = catalog.plant, config.stories, config.seed
    clock = make_clock(config.horizon_start, config.scale.weeks)
    masters = build_masters(plant, config.scale)
    shifts = pd.concat([shift_table(site, clock) for site in SITES], ignore_index=True)
    plan = plan_orders(masters.lines, masters.products, masters.routings, shifts, stream(seed, "orders"))
    degradations = simulate_failures(masters.assets, plant, stories, clock.minutes, stream(seed, "failures"))
    failures = failure_frame(degradations, clock.minutes)
    preventive = plan_preventive(masters.assets, shifts, stories, clock.minutes, stream(seed, "preventive"))
    instruments = plan_instrument_work(masters.assets, stories, clock.minutes)
    codes = state_codes(catalog.losses)
    minutes = build_minute_states(masters.assets, shifts, plan.line_shifts, preventive, failures, codes, stories,
                                  clock.minutes, stream(seed, "operations"))
    maintenance = build_maintenance(failures, preventive, instruments, masters.assets, plant, stream(seed, "cmms"))
    counts = shift_counts(masters.assets, shifts, plan.line_shifts, masters.routings, minutes, stories, stream(seed, "counts"))
    readings = sensor_readings(masters.sensors, masters.assets, plant, minutes, degradations, instruments, stories, clock,
                               config.scale.sample_minutes, stream(seed, "sensors"))
    states = state_intervals(minutes, codes, catalog.losses)
    tables = {
        "site": masters.sites, "line": masters.lines, "asset": masters.assets, "component": masters.components,
        "sensor": masters.sensors, "product": masters.products, "routing": masters.routings,
        "shift": _timed(shifts.assign(planned_break_minutes=BREAK_MINUTES), clock, ("start_minute", "end_minute")),
        "production_order": _timed(plan.orders, clock, ("planned_start_minute", "planned_end_minute")),
        "machine_state": _timed(states, clock, ("start_minute", "end_minute")),
        "production_count": counts,
        "sensor_reading": readings,
        "work_order": _timed(_due_dates(maintenance.work_orders, config.horizon_start), clock,
                             ("created_minute", "started_minute", "closed_minute")),
        "failure_event": _timed(maintenance.failure_events, clock, ("failed_minute", "restored_minute")),
    }
    facts = story_facts(tables, stories)
    return World(clock, tables, maintenance.missing_code_ids, maintenance.duplicates, facts)


def _timed(frame: pd.DataFrame, clock: Clock, columns: tuple[str, ...]) -> pd.DataFrame:
    """Replace minute columns with naive UTC timestamps named without the _minute suffix."""
    result = frame.copy()
    base = pd.Timestamp(clock.start).tz_localize(None)
    for column in columns:
        name = column.removesuffix("_minute") + "_at" if column.endswith("_minute") else column
        result[name] = base + pd.to_timedelta(result.pop(column), unit="min")
    return result


def _due_dates(orders: pd.DataFrame, horizon_start: object) -> pd.DataFrame:
    """Preventive due days as calendar dates (None for other work)."""
    result = orders.copy()
    days = result.pop("due_day")
    result["due_date"] = [None if pd.isna(d) else horizon_start + timedelta(days=int(d)) for d in days]
    return result
