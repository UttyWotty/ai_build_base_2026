"""Generation parameters: scale, horizon, and the planted stories, each with an explicit documented default.

A GenerationConfig fully determines the generated world together with its seed.
Tests use smaller ScaleConfig values; the defaults match the scale described in docs/plan.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

DEFAULT_SEED = 20260929
# A Monday, so every simulated week runs Monday to Sunday.
HORIZON_START = date(2024, 9, 30)
DEFAULT_WEEKS = 104
WEEKS_PER_QUARTER = 13


@dataclass(frozen=True)
class ScaleConfig:
    """Entity counts and demand volume."""

    supplier_count: int = 40
    part_count: int = 300
    customer_count: int = 120
    weeks: int = DEFAULT_WEEKS
    sales_lines_per_week: int = 580
    # Share of parts stocked at two plants instead of one.
    two_plant_share: float = 0.4


@dataclass(frozen=True)
class StoryConfig:
    """The four planted stories that give demo questions real answers."""

    # Supplier OTD ramps from its normal level down to degraded_on_time_share across this window, then stays there.
    degradation_start_week: int = 65
    degradation_weeks: int = WEEKS_PER_QUARTER
    degraded_on_time_share: float = 0.70
    # Inbound freight from this origin country into this plant is multiplied during the window.
    freight_spike_origin_country: str = "CN"
    freight_spike_plant_id: str = "US01"
    freight_spike_start_week: int = 52
    freight_spike_weeks: int = WEEKS_PER_QUARTER
    freight_spike_multiplier: float = 1.8
    # Reorder levels for this plant and part category are multiplied for the whole horizon.
    overstock_plant_id: str = "DE01"
    overstock_category: str = "Bearings"
    overstock_multiplier: float = 3.0
    # Aftermarket customers request short lead times, so committed dates often land after requested dates.
    short_request_segment: str = "Aftermarket"


@dataclass(frozen=True)
class GenerationConfig:
    """Everything needed to generate one world."""

    seed: int = DEFAULT_SEED
    horizon_start: date = HORIZON_START
    scale: ScaleConfig = field(default_factory=ScaleConfig)
    stories: StoryConfig = field(default_factory=StoryConfig)
