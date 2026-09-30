"""The plant validator: references between sensors, components, and failure modes, ranges, names, and coverage.

Each test breaks one thing in a valid plant and expects exactly the matching issue.
The unbroken plant must produce no issues at all.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.plant_parser import parse_plant
from pdm_oee.core.plant_validator import validate_plant
from tests.pdm_oee.core.catalog_fixtures import RawDocument, raw_plant


def issues_for(document: RawDocument) -> list[str]:
    return [str(issue) for issue in validate_plant(parse_plant(document))]


def pump(document: RawDocument) -> dict:
    return document["asset_classes"]["pump_station"]


def test_valid_plant_has_no_issues() -> None:
    assert issues_for(raw_plant()) == []
    model = parse_plant(raw_plant())
    modes = model.asset_classes["pump_station"].failure_modes
    assert modes["bearing_wear"].predictable and not modes["seal_rupture"].predictable


@pytest.mark.parametrize("field, value, message", [
    ("type", "noise", "unknown sensor type 'noise'"),
    ("component", "impeller", "unknown component 'impeller'"),
    ("normal_range", [3.0, 0.5], "low < high"),
])
def test_bad_sensor_is_reported(field: str, value: object, message: str) -> None:
    document = raw_plant()
    pump(document)["sensors"]["bearing_vibration"][field] = value
    assert any(message in issue for issue in issues_for(document))


def test_failure_mode_references_are_checked() -> None:
    document = raw_plant()
    mode = pump(document)["failure_modes"]["bearing_wear"]
    mode["symptoms"] = ["bearing_vibration", "flow_rate", "bearing_vibration"]
    mode["component"] = "impeller"
    issues = issues_for(document)
    assert any("unknown symptom sensor(s): flow_rate" in i for i in issues)
    assert any("symptoms must not repeat" in i for i in issues)
    assert any("unknown component 'impeller'" in i for i in issues)


def test_pf_interval_must_match_whether_symptoms_exist() -> None:
    document = raw_plant()
    del pump(document)["failure_modes"]["bearing_wear"]["pf_interval_days"]
    pump(document)["failure_modes"]["seal_rupture"]["pf_interval_days"] = 2
    issues = issues_for(document)
    assert any("needs pf_interval_days" in i for i in issues)
    assert any("meaningless without symptom sensors" in i for i in issues)


def test_every_component_needs_a_failure_mode() -> None:
    document = raw_plant()
    del pump(document)["failure_modes"]["seal_rupture"]
    assert issues_for(document) == ["asset_classes.pump_station.components.seal: has no failure mode"]


def test_failure_mode_ids_are_unique_across_classes() -> None:
    document = raw_plant()
    document["asset_classes"]["spare_station"] = pump(raw_plant())
    assert "failure_modes.bearing_wear: id is used by 2 asset classes; it must be unique" in issues_for(document)


def test_names_must_be_snake_case() -> None:
    document = raw_plant()
    pump(document)["components"]["Seal"] = pump(document)["components"].pop("seal")
    assert any("name 'Seal' must be lowercase snake_case" in i for i in issues_for(document))
