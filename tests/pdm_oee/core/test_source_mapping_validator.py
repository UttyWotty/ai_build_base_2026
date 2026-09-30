"""The source mapping validator: every reason and state mapped once per site, clean quality codes, reachable units,
and CMMS codes and keywords that identify exactly one failure mode.

Each test changes the checked-in mappings in one way and expects the matching issue.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from pdm_oee.core.source_mapping_parser import parse_source_mappings
from pdm_oee.core.source_mapping_validator import validate_source_mappings
from pdm_oee.data_pipeline.semantic_files import load_catalog

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "pdm"
CATALOG = load_catalog(SEMANTIC_DIR)


def raw() -> dict:
    return yaml.safe_load((SEMANTIC_DIR / "source_mappings.yaml").read_text(encoding="utf-8"))


def issues_for(document: dict) -> list[str]:
    return [str(i) for i in validate_source_mappings(parse_source_mappings(document), CATALOG)]


def test_checked_in_mappings_are_valid() -> None:
    assert issues_for(raw()) == []


def test_reasons_and_states_are_mapped_once_per_site() -> None:
    document = raw()
    reasons = document["sites"]["US1"]["reasons"]
    del reasons["NOOP"]
    reasons["CO2"] = "changeover"
    reasons["XX"] = "coffee"
    del document["sites"]["DE1"]["states"]["GEPLANT"]
    issues = issues_for(document)
    assert "sites.US1: reason 'no_operator' is not mapped" in issues
    assert "sites.US1: reason 'changeover' is mapped by 2 codes" in issues
    assert "sites.US1: 'coffee' is not a governed stop reason" in issues
    assert "sites.DE1: state 'planned_stop' is not mapped" in issues


def test_quality_units_and_site_numbers() -> None:
    document = raw()
    document["sites"]["US1"]["quality"]["bad"] = ["192"]
    document["sites"]["DE1"]["number"] = 1
    del document["printed_units"]["A"]
    issues = issues_for(document)
    assert "sites.US1: quality codes must be non-empty and good and bad must not overlap" in issues
    assert "sites: site number 1 is used twice" in issues
    assert "printed_units: no printed unit converts to ampere" in issues


def test_cmms_codes_and_keywords() -> None:
    document = raw()
    cmms = document["cmms"]
    del cmms["failure_codes"]["MOT-HOT"]
    cmms["failure_keywords"]["gearbox_wear"] = ["gearbox", "motor"]
    del cmms["work_types"]["INST"]
    issues = issues_for(document)
    assert "cmms.failure_codes: 'motor_overheating' has no code" in issues
    assert "cmms.failure_keywords.gearbox_wear: 'motor' also matches 'motor_overheating'" in issues
    assert "cmms.work_types: 'instrument' has no code" in issues
