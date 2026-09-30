"""Generation parameters: horizon, scale, and the planted stories, each with an explicit documented default.

A GenerationConfig fully determines the generated plant together with its seed.
Tests use a shorter horizon and move the story dates inside it; the defaults match docs/plan.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

DEFAULT_SEED = 20260929
# A Monday, so every simulated week runs Monday to Sunday; 52 weeks end on Sunday 2026-09-27.
HORIZON_START = date(2025, 9, 29)
DEFAULT_WEEKS = 52


@dataclass(frozen=True)
class ScaleConfig:
    """Horizon length and plant size."""

    weeks: int = DEFAULT_WEEKS
    lines_per_site: int = 3
    sample_minutes: int = 10


@dataclass(frozen=True)
class StoryConfig:
    """The six planted stories; days count from the horizon start."""

    # A spindle bearing failure with a clean six-day warning, placed in the last four months (the test period).
    bearing_asset_id: str = "US1-L2-01"
    bearing_failure_day: int = 300
    # A hydraulic pump wearing out over three weeks.
    pump_asset_id: str = "DE1-L1-03"
    pump_failure_day: int = 330
    # A temperature sensor replaced with a calibration offset and no failure behind it.
    calibration_asset_id: str = "DE1-L3-01"
    calibration_sensor: str = "spindle_temperature"
    calibration_day: int = 150
    calibration_offset: float = 6.0
    # One line gets preventive maintenance at this fraction of the normal interval.
    over_maintained_line_id: str = "US1-L3"
    over_maintenance_interval_factor: float = 0.5
    # Coolant runs hotter in summer on this line, and scrap rises with coolant temperature.
    coolant_line_id: str = "DE1-L2"
    coolant_summer_rise: float = 6.0
    scrap_share_per_degree: float = 0.012
    # This conveyor has frequent stops under five minutes.
    small_stop_asset_id: str = "US1-L1-04"
    small_stops_per_hour: float = 6.0


@dataclass(frozen=True)
class GenerationConfig:
    """Everything needed to generate one plant."""

    seed: int = DEFAULT_SEED
    horizon_start: date = HORIZON_START
    scale: ScaleConfig = field(default_factory=ScaleConfig)
    stories: StoryConfig = field(default_factory=StoryConfig)
