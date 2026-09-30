"""Closed vocabularies of the catalog: OEE factors, loss sources, machine states, work types, measure grains and units, metric formats, teams, and sensor units.

Every enum value is the exact spelling used in the YAML files.
Parsers convert YAML text into these members so typos fail loudly with the list of allowed values.
"""
from __future__ import annotations

from enum import Enum


class Factor(str, Enum):
    """The OEE factor a loss reduces."""

    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    QUALITY = "quality"


class LossSource(str, Enum):
    """Where the time or parts of a loss come from, which fixes the OEE factor it can belong to."""

    STOP_REASON = "stop_reason"
    SHORT_STOP = "short_stop"
    SPEED_GAP = "speed_gap"
    STARTUP_SCRAP = "startup_scrap"
    PRODUCTION_SCRAP = "production_scrap"


class Grain(str, Enum):
    """The level at which a measure is computed before any roll-up."""

    ASSET_SHIFT = "asset_shift"
    ASSET_COMPONENT = "asset_component"
    ASSET = "asset"


class MeasureUnit(str, Enum):
    """The unit a measure is expressed in."""

    MINUTES = "minutes"
    HOURS = "hours"
    PARTS = "parts"
    COUNT = "count"


class MetricFormat(str, Enum):
    """How a metric value is presented, which also constrains its measures' units."""

    PERCENT = "percent"
    HOURS = "hours"


class Team(str, Enum):
    """Teams that own metrics."""

    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    QUALITY = "quality"


class SensorUnit(str, Enum):
    """Canonical engineering units for sensor readings; sources in other units are converted during conform."""

    MM_PER_S = "mm_per_s"
    DEG_C = "deg_c"
    RPM = "rpm"
    BAR = "bar"
    AMPERE = "ampere"


class MachineState(str, Enum):
    """What an asset is doing, as the MES reports it after mapping."""

    RUNNING = "running"
    PLANNED_STOP = "planned_stop"
    UNPLANNED_STOP = "unplanned_stop"


class WorkType(str, Enum):
    """Kinds of CMMS work order."""

    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    INSTRUMENT = "instrument"
