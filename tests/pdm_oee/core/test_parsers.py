"""Shape errors from the parsers: unknown fields, wrong types, bad enum values, and bad numbers, each with its path.

Parsers never guess; every error names the dotted path of the offending field.
Cross-reference problems are left to the validators and are not tested here.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.errors import SemanticParseError
from pdm_oee.core.loss_parser import parse_losses
from pdm_oee.core.metric_parser import parse_measures, parse_metric
from pdm_oee.core.plant_parser import parse_plant
from tests.pdm_oee.core.catalog_fixtures import (
    raw_losses,
    raw_measures,
    raw_metric,
    raw_plant,
)


def test_unknown_field_is_rejected_with_its_path() -> None:
    document = raw_plant()
    document["asset_classes"]["pump_station"]["sensors"]["bearing_vibration"]["units"] = "mm/s"
    with pytest.raises(SemanticParseError, match="asset_classes.pump_station.sensors.bearing_vibration: unknown field"):
        parse_plant(document)


def test_bad_enum_lists_the_allowed_values() -> None:
    document = raw_losses()
    document["losses"]["breakdowns"]["factor"] = "uptime"
    with pytest.raises(SemanticParseError, match="losses.breakdowns.factor: 'uptime' is not one of: availability, performance, quality"):
        parse_losses(document)


@pytest.mark.parametrize("field, value, message", [
    ("repair_hours", 0, "expected a number greater than zero"),
    ("repair_hours", True, "expected a number greater than zero"),
    ("pf_interval_days", "six", "expected a number greater than zero"),
])
def test_failure_mode_numbers_must_be_positive(field: str, value: object, message: str) -> None:
    document = raw_plant()
    document["asset_classes"]["pump_station"]["failure_modes"]["bearing_wear"][field] = value
    with pytest.raises(SemanticParseError, match=message):
        parse_plant(document)


def test_normal_range_needs_two_numbers() -> None:
    document = raw_plant()
    document["asset_classes"]["pump_station"]["sensors"]["bearing_vibration"]["normal_range"] = [1]
    with pytest.raises(SemanticParseError, match="normal_range: expected a list of two numbers"):
        parse_plant(document)


def test_measure_parameters_must_be_numbers() -> None:
    document = raw_measures()
    document["measures"]["run_time"]["parameters"] = {"small_stop_threshold_minutes": "five"}
    with pytest.raises(SemanticParseError, match="measures.run_time.parameters.small_stop_threshold_minutes: expected a number"):
        parse_measures(document)
    assert parse_measures(raw_measures())["run_time"].parameters == {"small_stop_threshold_minutes": 5.0}


def test_metric_errors_name_the_file() -> None:
    with pytest.raises(SemanticParseError, match="oee.yaml.owner: 'finance' is not one of"):
        parse_metric(raw_metric(owner="finance"), "oee.yaml")
