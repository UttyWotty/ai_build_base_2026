"""Consistency checks for the plant model: names, references between sensors, components, and failure modes, and ranges.

Every component must have at least one failure mode, and failure mode ids must be unique across all asset classes,
because work orders and alerts refer to a failure mode by id alone. All issues are collected, never just the first.
"""
from __future__ import annotations

from collections import Counter

from pdm_oee.core.errors import ValidationIssue
from pdm_oee.core.identifiers import IDENTIFIER_RULE, is_valid_identifier
from pdm_oee.core.plant_model import AssetClass, PlantModel


def validate_plant(plant: PlantModel) -> list[ValidationIssue]:
    """Every problem in the plant model."""
    issues = [ValidationIssue(f"sensor_types.{name}", f"name {IDENTIFIER_RULE}")
              for name in plant.sensor_types if not is_valid_identifier(name)]
    for asset_class in plant.asset_classes.values():
        issues += _check_class(asset_class, plant)
    counts = Counter(mode for c in plant.asset_classes.values() for mode in c.failure_modes)
    issues += [ValidationIssue(f"failure_modes.{mode}", f"id is used by {n} asset classes; it must be unique")
               for mode, n in sorted(counts.items()) if n > 1]
    return issues


def _check_class(asset_class: AssetClass, plant: PlantModel) -> list[ValidationIssue]:
    where = f"asset_classes.{asset_class.id}"
    names = [asset_class.id, *asset_class.components, *asset_class.sensors, *asset_class.failure_modes]
    issues = [ValidationIssue(where, f"name '{n}' {IDENTIFIER_RULE}") for n in names if not is_valid_identifier(n)]
    for sensor in asset_class.sensors.values():
        at = f"{where}.sensors.{sensor.id}"
        if sensor.sensor_type not in plant.sensor_types:
            issues.append(ValidationIssue(at, f"unknown sensor type '{sensor.sensor_type}'"))
        if sensor.component not in asset_class.components:
            issues.append(ValidationIssue(at, f"unknown component '{sensor.component}'"))
        if sensor.normal_range[0] >= sensor.normal_range[1]:
            issues.append(ValidationIssue(at, "normal_range must be [low, high] with low < high"))
    for mode in asset_class.failure_modes.values():
        issues += _check_failure_mode(where, asset_class, mode.id)
    covered = {m.component for m in asset_class.failure_modes.values()}
    issues += [ValidationIssue(f"{where}.components.{c}", "has no failure mode")
               for c in asset_class.components if c not in covered]
    return issues


def _check_failure_mode(where: str, asset_class: AssetClass, mode_id: str) -> list[ValidationIssue]:
    mode = asset_class.failure_modes[mode_id]
    at = f"{where}.failure_modes.{mode_id}"
    issues = []
    if mode.component not in asset_class.components:
        issues.append(ValidationIssue(at, f"unknown component '{mode.component}'"))
    unknown = [s for s in mode.symptoms if s not in asset_class.sensors]
    if unknown:
        issues.append(ValidationIssue(at, f"unknown symptom sensor(s): {', '.join(unknown)}"))
    if len(set(mode.symptoms)) != len(mode.symptoms):
        issues.append(ValidationIssue(at, "symptoms must not repeat"))
    if mode.predictable and mode.pf_interval_days is None:
        issues.append(ValidationIssue(at, "a failure mode with symptoms needs pf_interval_days"))
    if not mode.predictable and mode.pf_interval_days is not None:
        issues.append(ValidationIssue(at, "pf_interval_days is meaningless without symptom sensors"))
    return issues
