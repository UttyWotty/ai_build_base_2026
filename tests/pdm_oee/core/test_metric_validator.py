"""The metric validator: measure references, grains, units against formats, duplicate ids, terms, and look-alikes.

Each test builds metrics over the fixture measures and expects the matching issue.
The build_catalog tests check that all issues are collected and that a clean catalog indexes metrics by id.
"""
from __future__ import annotations

import pytest

from pdm_oee.core.catalog import build_catalog
from pdm_oee.core.errors import CatalogValidationError
from pdm_oee.core.loss_parser import parse_losses
from pdm_oee.core.metric_parser import parse_measures, parse_metric
from pdm_oee.core.metric_validator import validate_metrics
from pdm_oee.core.plant_parser import parse_plant
from tests.pdm_oee.core.catalog_fixtures import (
    raw_losses,
    raw_measures,
    raw_metric,
    raw_plant,
)

MEASURES = parse_measures(raw_measures())


def issues_for(*documents: dict) -> list[str]:
    metrics = [parse_metric(d, f"m{i}.yaml") for i, d in enumerate(documents)]
    return [str(issue) for issue in validate_metrics(MEASURES, metrics)]


def test_valid_metrics_have_no_issues() -> None:
    mtbf = raw_metric(id="mtbf", label="MTBF", synonyms=[], numerator="operating_hours",
                      denominator="functional_failures", format="hours", owner="maintenance")
    assert issues_for(raw_metric(), mtbf) == []


@pytest.mark.parametrize("overrides, message", [
    ({"numerator": "speed"}, "unknown measure(s): speed"),
    ({"numerator": "planned_production_time"}, "numerator and denominator must differ"),
    ({"numerator": "operating_hours"}, "numerator grain asset_component differs from denominator grain asset_shift"),
    ({"numerator": "total_count"}, "a percent needs one unit, not parts over minutes"),
    ({"format": "hours"}, "an hours metric needs hours over a count, not minutes over minutes"),
])
def test_ratio_problems_are_reported(overrides: dict, message: str) -> None:
    assert any(message in issue for issue in issues_for(raw_metric(**overrides)))


def test_ids_and_terms_resolve_to_one_metric() -> None:
    same_id = raw_metric(label="Availability again", synonyms=[])
    rival = raw_metric(id="uptime", label="Uptime", synonyms=["UPTIME-SHARE"])
    issues = issues_for(raw_metric(), same_id, rival)
    assert "m1.yaml: id 'availability' is already defined in m0.yaml" in issues
    assert "m2.yaml: term 'uptime share' already belongs to metric 'availability'" in issues


def test_look_alikes_must_exist_and_be_mutual() -> None:
    strict = raw_metric(id="strict", label="Strict", synonyms=[], not_to_be_confused_with=["availability", "strict", "ghost"])
    issues = issues_for(raw_metric(), strict)
    assert "m1.yaml: 'availability' must also list 'strict' as a look-alike" in issues
    assert "m1.yaml: a metric cannot be its own look-alike" in issues
    assert "m1.yaml: look-alike 'ghost' is not a defined metric" in issues


def test_build_catalog_collects_issues_from_every_part() -> None:
    plant, losses = raw_plant(), raw_losses()
    plant["sensor_types"]["vibration"]["unit"] = "mm_per_s"
    del plant["asset_classes"]["pump_station"]["failure_modes"]["seal_rupture"]
    losses["planned_stop_reasons"] = {}
    with pytest.raises(CatalogValidationError) as raised:
        build_catalog(parse_plant(plant), parse_losses(losses), MEASURES, [parse_metric(raw_metric(numerator="speed"), "m.yaml")])
    assert len(raised.value.issues) == 3


def test_build_catalog_indexes_metrics_by_id() -> None:
    catalog = build_catalog(parse_plant(raw_plant()), parse_losses(raw_losses()), MEASURES,
                            [parse_metric(raw_metric(), "m.yaml")])
    assert catalog.metric("availability") is not None and catalog.metric("missing") is None
