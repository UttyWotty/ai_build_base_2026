"""Parses the plant document (sensor types and asset classes) into a PlantModel.

Shape errors name the dotted path of the offending field; unknown fields are rejected to catch typos.
Cross-references (sensor types, components, symptoms) are checked by the plant validator, not here.
"""
from __future__ import annotations

from pdm_oee.core.enums import SensorUnit
from pdm_oee.core.field_readers import (
    RawMapping,
    as_mapping,
    join_path,
    optional_str_list,
    reject_unknown_keys,
    require_enum,
    require_mapping,
    require_number_pair,
    require_positive_number,
    require_str,
)
from pdm_oee.core.plant_model import (
    AssetClass,
    Component,
    FailureMode,
    PlantModel,
    SensorSpec,
    SensorType,
)

ROOT_KEYS = frozenset({"sensor_types", "asset_classes"})
SENSOR_TYPE_KEYS = frozenset({"label", "unit"})
CLASS_KEYS = frozenset({"label", "components", "sensors", "failure_modes"})
COMPONENT_KEYS = frozenset({"label"})
SENSOR_KEYS = frozenset({"label", "type", "component", "normal_range"})
FAILURE_MODE_KEYS = frozenset({"label", "component", "symptoms", "pf_interval_days", "repair_hours", "recommended_action"})
PF_INTERVAL_KEY = "pf_interval_days"


def parse_plant(raw: object) -> PlantModel:
    """Turn the plant document into a PlantModel."""
    root = as_mapping(raw, "plant")
    reject_unknown_keys(root, ROOT_KEYS, "plant")
    types = {name: _sensor_type(name, as_mapping(v, f"sensor_types.{name}"))
             for name, v in require_mapping(root, "sensor_types", "").items()}
    classes = {name: _asset_class(name, as_mapping(v, f"asset_classes.{name}"))
               for name, v in require_mapping(root, "asset_classes", "").items()}
    return PlantModel(sensor_types=types, asset_classes=classes)


def _sensor_type(name: str, raw: RawMapping) -> SensorType:
    path = f"sensor_types.{name}"
    reject_unknown_keys(raw, SENSOR_TYPE_KEYS, path)
    return SensorType(name, require_str(raw, "label", path), require_enum(raw, "unit", path, SensorUnit))


def _asset_class(name: str, raw: RawMapping) -> AssetClass:
    path = f"asset_classes.{name}"
    reject_unknown_keys(raw, CLASS_KEYS, path)
    return AssetClass(
        id=name,
        label=require_str(raw, "label", path),
        components={c: _component(c, as_mapping(v, join_path(path, f"components.{c}")), path)
                    for c, v in require_mapping(raw, "components", path).items()},
        sensors={s: _sensor(s, as_mapping(v, join_path(path, f"sensors.{s}")), path)
                 for s, v in require_mapping(raw, "sensors", path).items()},
        failure_modes={f: _failure_mode(f, as_mapping(v, join_path(path, f"failure_modes.{f}")), path)
                       for f, v in require_mapping(raw, "failure_modes", path).items()},
    )


def _component(name: str, raw: RawMapping, class_path: str) -> Component:
    path = join_path(class_path, f"components.{name}")
    reject_unknown_keys(raw, COMPONENT_KEYS, path)
    return Component(name, require_str(raw, "label", path))


def _sensor(name: str, raw: RawMapping, class_path: str) -> SensorSpec:
    path = join_path(class_path, f"sensors.{name}")
    reject_unknown_keys(raw, SENSOR_KEYS, path)
    return SensorSpec(name, require_str(raw, "label", path), require_str(raw, "type", path),
                      require_str(raw, "component", path), require_number_pair(raw, "normal_range", path))


def _failure_mode(name: str, raw: RawMapping, class_path: str) -> FailureMode:
    path = join_path(class_path, f"failure_modes.{name}")
    reject_unknown_keys(raw, FAILURE_MODE_KEYS, path)
    pf_interval = require_positive_number(raw, PF_INTERVAL_KEY, path) if PF_INTERVAL_KEY in raw else None
    return FailureMode(
        id=name, label=require_str(raw, "label", path), component=require_str(raw, "component", path),
        symptoms=optional_str_list(raw, "symptoms", path), pf_interval_days=pf_interval,
        repair_hours=require_positive_number(raw, "repair_hours", path),
        recommended_action=require_str(raw, "recommended_action", path),
    )
