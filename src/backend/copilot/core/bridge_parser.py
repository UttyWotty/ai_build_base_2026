"""Parses the bridge document (semantic/bridge/bridge.yaml) into a BridgeCatalog.

Shape errors name the dotted path of the offending field, and unknown fields are rejected to catch typos.
Whether the ids exist in the plant catalog and the supply world is checked by the bridge validator, not here.
"""
from __future__ import annotations

from copilot.core.bridge_model import (
    BridgeCatalog,
    EmergencySource,
    LineLink,
    SiteLink,
    SparePart,
    StockPolicy,
    TransferTerms,
)
from pdm_oee.core.errors import SemanticParseError
from pdm_oee.core.field_readers import (
    RawMapping,
    as_mapping,
    join_path,
    optional_mapping,
    reject_unknown_keys,
    require_mapping,
    require_positive_number,
    require_str,
    require_str_list,
    require_value,
)

ROOT_KEYS = frozenset({"sites", "spare_parts", "stock_policy", "transfer", "lines", "customer_risk"})
SITE_KEYS = frozenset({"plant_id", "label"})
SPARE_KEYS = frozenset({"spare_part_id", "label", "unit_cost_usd", "quantity_per_repair", "supplier_id",
                        "contracted_lead_time_days", "emergency"})
EMERGENCY_KEYS = frozenset({"lead_time_hours", "price_multiplier"})
POLICY_KEYS = frozenset({"initial", "reorder_point", "order_up_to"})
TRANSFER_KEYS = frozenset({"lead_time_hours", "cost_usd"})
LINE_KEYS = frozenset({"part_ids", "contribution_usd_per_unit"})
RISK_KEYS = frozenset({"dispatch_buffer_days"})


def parse_bridge(raw: object) -> BridgeCatalog:
    """Turn the bridge document into a BridgeCatalog."""
    root = as_mapping(raw, "bridge")
    reject_unknown_keys(root, ROOT_KEYS, "bridge")
    transfer = require_mapping(root, "transfer", "bridge")
    reject_unknown_keys(transfer, TRANSFER_KEYS, "bridge.transfer")
    risk = require_mapping(root, "customer_risk", "bridge")
    reject_unknown_keys(risk, RISK_KEYS, "bridge.customer_risk")
    return BridgeCatalog(
        sites=_sites(require_mapping(root, "sites", "bridge")),
        spares=_spares(require_mapping(root, "spare_parts", "bridge")),
        policies=_policies(require_mapping(root, "stock_policy", "bridge")),
        transfer=TransferTerms(require_positive_number(transfer, "lead_time_hours", "bridge.transfer"),
                               _require_non_negative(transfer, "cost_usd", "bridge.transfer")),
        lines=_lines(require_mapping(root, "lines", "bridge")),
        dispatch_buffer_days=_require_non_negative(risk, "dispatch_buffer_days", "bridge.customer_risk"),
    )


def _sites(raw: RawMapping) -> dict[str, SiteLink]:
    sites = {}
    for site_id, value in raw.items():
        path = join_path("bridge.sites", site_id)
        entry = as_mapping(value, path)
        reject_unknown_keys(entry, SITE_KEYS, path)
        sites[site_id] = SiteLink(site_id, require_str(entry, "plant_id", path), require_str(entry, "label", path))
    return sites


def _spares(raw: RawMapping) -> dict[str, SparePart]:
    spares = {}
    for component, value in raw.items():
        path = join_path("bridge.spare_parts", component)
        entry = as_mapping(value, path)
        reject_unknown_keys(entry, SPARE_KEYS, path)
        spares[component] = SparePart(
            component=component,
            spare_part_id=require_str(entry, "spare_part_id", path),
            label=require_str(entry, "label", path),
            unit_cost_usd=require_positive_number(entry, "unit_cost_usd", path),
            quantity_per_repair=_require_int(entry, "quantity_per_repair", path, minimum=1),
            supplier_id=require_str(entry, "supplier_id", path),
            contracted_lead_time_days=_require_int(entry, "contracted_lead_time_days", path, minimum=1),
            emergency=_emergency(optional_mapping(entry, "emergency", path), join_path(path, "emergency")),
        )
    return spares


def _emergency(raw: RawMapping, path: str) -> EmergencySource | None:
    if not raw:
        return None
    reject_unknown_keys(raw, EMERGENCY_KEYS, path)
    return EmergencySource(require_positive_number(raw, "lead_time_hours", path),
                           require_positive_number(raw, "price_multiplier", path))


def _policies(raw: RawMapping) -> dict[tuple[str, str], StockPolicy]:
    policies = {}
    for site_id, value in raw.items():
        site_path = join_path("bridge.stock_policy", site_id)
        for spare_id, entry_value in as_mapping(value, site_path).items():
            path = join_path(site_path, spare_id)
            entry = as_mapping(entry_value, path)
            reject_unknown_keys(entry, POLICY_KEYS, path)
            policies[(site_id, spare_id)] = StockPolicy(
                site_id, spare_id, _require_int(entry, "initial", path, minimum=0),
                _require_int(entry, "reorder_point", path, minimum=0), _require_int(entry, "order_up_to", path, minimum=1))
    return policies


def _lines(raw: RawMapping) -> dict[str, LineLink]:
    lines = {}
    for line_id, value in raw.items():
        path = join_path("bridge.lines", line_id)
        entry = as_mapping(value, path)
        reject_unknown_keys(entry, LINE_KEYS, path)
        part_ids = require_str_list(entry, "part_ids", path) if entry.get("part_ids") else ()
        lines[line_id] = LineLink(line_id, part_ids, require_positive_number(entry, "contribution_usd_per_unit", path))
    return lines


def _require_int(raw: RawMapping, key: str, path: str, minimum: int) -> int:
    value = require_value(raw, key, path)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SemanticParseError(join_path(path, key), f"expected a whole number of at least {minimum}")
    return value


def _require_non_negative(raw: RawMapping, key: str, path: str) -> float:
    value = require_value(raw, key, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise SemanticParseError(join_path(path, key), "expected a number of at least zero")
    return float(value)
