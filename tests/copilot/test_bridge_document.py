"""Tests that parse and validate the repository's bridge document and reject malformed or dangling definitions.

The real semantic/bridge/bridge.yaml must parse; validation runs against a hand-built set of known ids.
Every dangling reference is reported in one error.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from copilot.core.bridge_parser import parse_bridge
from copilot.core.bridge_validator import KnownIds, validate_bridge
from copilot.core.errors import BridgeValidationError
from copilot.data_pipeline.bridge_files import load_bridge
from pdm_oee.core.errors import SemanticParseError

SEMANTIC_DIR = Path(__file__).resolve().parents[2] / "semantic" / "bridge"


def test_repository_bridge_parses_with_every_component_spare_and_line() -> None:
    bridge = load_bridge(SEMANTIC_DIR)
    assert set(bridge.sites) == {"US1", "DE1"} and bridge.sites["US1"].plant_id == "US01"
    assert bridge.spare_for_component("spindle_bearing").supplier_id == "V10001"
    assert bridge.spare_for_component("tool_changer") is None
    assert len(bridge.lines) == 6 and bridge.lines["DE1-L3"].part_ids == ()
    assert len(bridge.policies) == 12 and bridge.transfer.lead_time_hours == 48


def test_validation_lists_every_dangling_reference() -> None:
    bridge = load_bridge(SEMANTIC_DIR)
    known = KnownIds(frozenset({"US1"}), frozenset({"US1-L1"}), frozenset({"spindle_bearing"}), frozenset({"US01"}),
                     frozenset({"V10001"}), frozenset())
    with pytest.raises(BridgeValidationError) as error:
        validate_bridge(bridge, known)
    text = str(error.value)
    assert "sites.DE1: not a plant site" in text and "spare_parts.gearbox: not a plant component" in text
    assert "V10030 is not a supply supplier" in text and "part P-000050 is not a supply part" in text


def test_unknown_fields_and_bad_numbers_are_rejected() -> None:
    minimal = {"sites": {}, "spare_parts": {}, "stock_policy": {}, "lines": {},
               "transfer": {"lead_time_hours": 48, "cost_usd": 0}, "customer_risk": {"dispatch_buffer_days": 2}}
    assert parse_bridge(minimal).transfer.cost_usd == 0
    with pytest.raises(SemanticParseError, match="unknown field"):
        parse_bridge({**minimal, "extra": 1})
    with pytest.raises(SemanticParseError, match="lead_time_hours"):
        parse_bridge({**minimal, "transfer": {"lead_time_hours": 0, "cost_usd": 1}})


def test_policy_must_reorder_below_its_order_up_to_level() -> None:
    bridge = load_bridge(SEMANTIC_DIR)
    broken = {**bridge.policies}
    key = ("US1", "SP-1001")
    broken[key] = type(broken[key])("US1", "SP-1001", 2, 2, 2)
    known = KnownIds(frozenset(bridge.sites), frozenset(bridge.lines), frozenset(bridge.spares), frozenset({"US01", "DE01"}),
                     frozenset(s.supplier_id for s in bridge.spares.values()),
                     frozenset(p for link in bridge.lines.values() for p in link.part_ids))
    validate_bridge(bridge, known)
    with pytest.raises(BridgeValidationError, match="reorder_point must be below"):
        validate_bridge(type(bridge)(bridge.sites, bridge.spares, broken, bridge.transfer, bridge.lines, 2.0), known)
