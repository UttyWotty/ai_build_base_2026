"""The governed plant model: sensor types, and asset classes with their components, sensors, and failure modes.

It describes kinds of equipment, not individual machines; sites, lines, and assets are generated master data.
A failure mode is predictable exactly when it declares symptom sensors, and only predictable modes are scored by the predictor.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pdm_oee.core.enums import SensorUnit


@dataclass(frozen=True)
class SensorType:
    """A kind of measurement with its canonical unit."""

    id: str
    label: str
    unit: SensorUnit


@dataclass(frozen=True)
class Component:
    """The part of an asset that fails and is repaired."""

    id: str
    label: str


@dataclass(frozen=True)
class SensorSpec:
    """One sensor position on an asset class: what it measures, on which component, and its healthy range."""

    id: str
    label: str
    sensor_type: str
    component: str
    normal_range: tuple[float, float]


@dataclass(frozen=True)
class FailureMode:
    """How a component fails, how the failure shows in the sensors, and how it is repaired."""

    id: str
    label: str
    component: str
    # Symptom sensors in the order they react; empty when the failure gives no sensor warning.
    symptoms: tuple[str, ...]
    pf_interval_days: float | None
    repair_hours: float
    recommended_action: str

    @property
    def predictable(self) -> bool:
        return bool(self.symptoms)


@dataclass(frozen=True)
class AssetClass:
    """A kind of equipment and everything declared about it."""

    id: str
    label: str
    components: Mapping[str, Component]
    sensors: Mapping[str, SensorSpec]
    failure_modes: Mapping[str, FailureMode]


@dataclass(frozen=True)
class PlantModel:
    """All sensor types and asset classes."""

    sensor_types: Mapping[str, SensorType]
    asset_classes: Mapping[str, AssetClass]
