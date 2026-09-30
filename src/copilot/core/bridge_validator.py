"""Checks that every id in the bridge resolves in the plant catalog and the supply world, and that policies are consistent.

The known ids are passed in as plain sets, so the checks run without loading either world.
Every issue is collected before failing, so one run lists all broken references.
"""
from __future__ import annotations

from dataclasses import dataclass

from copilot.core.bridge_model import BridgeCatalog
from copilot.core.errors import BridgeValidationError


@dataclass(frozen=True)
class KnownIds:
    """Ids that exist in the plant catalog and the generated supply world."""

    plant_sites: frozenset[str]
    plant_lines: frozenset[str]
    plant_components: frozenset[str]
    supply_plants: frozenset[str]
    supply_suppliers: frozenset[str]
    supply_parts: frozenset[str]


def validate_bridge(bridge: BridgeCatalog, known: KnownIds) -> None:
    """Raise BridgeValidationError listing every problem, or return when there is none."""
    issues = _site_issues(bridge, known) + _spare_issues(bridge, known) + _policy_issues(bridge) + _line_issues(bridge, known)
    if issues:
        raise BridgeValidationError(issues)


def _site_issues(bridge: BridgeCatalog, known: KnownIds) -> list[str]:
    issues = [f"sites.{s}: not a plant site" for s in bridge.sites if s not in known.plant_sites]
    issues += [f"sites.{s.site_id}: plant {s.plant_id} is not a supply plant"
               for s in bridge.sites.values() if s.plant_id not in known.supply_plants]
    issues += [f"sites: plant site {s} has no link" for s in sorted(known.plant_sites - set(bridge.sites))]
    return issues


def _spare_issues(bridge: BridgeCatalog, known: KnownIds) -> list[str]:
    issues = [f"spare_parts.{c}: not a plant component" for c in bridge.spares if c not in known.plant_components]
    issues += [f"spare_parts.{s.component}: supplier {s.supplier_id} is not a supply supplier"
               for s in bridge.spares.values() if s.supplier_id not in known.supply_suppliers]
    ids = [s.spare_part_id for s in bridge.spares.values()]
    issues += [f"spare_parts: spare part id {i} is used twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
    return issues


def _policy_issues(bridge: BridgeCatalog) -> list[str]:
    spare_ids = {s.spare_part_id for s in bridge.spares.values()}
    issues = []
    for site_id in sorted(bridge.sites):
        issues += [f"stock_policy.{site_id}: no policy for {spare}"
                   for spare in sorted(spare_ids) if (site_id, spare) not in bridge.policies]
    for (site_id, spare), policy in sorted(bridge.policies.items()):
        if site_id not in bridge.sites or spare not in spare_ids:
            issues.append(f"stock_policy.{site_id}.{spare}: unknown site or spare")
        elif not policy.reorder_point < policy.order_up_to:
            issues.append(f"stock_policy.{site_id}.{spare}: reorder_point must be below order_up_to")
    return issues


def _line_issues(bridge: BridgeCatalog, known: KnownIds) -> list[str]:
    issues = [f"lines.{line}: not a plant line" for line in bridge.lines if line not in known.plant_lines]
    issues += [f"lines: plant line {line} has no link" for line in sorted(known.plant_lines - set(bridge.lines))]
    issues += [f"lines.{link.line_id}: part {p} is not a supply part"
               for link in bridge.lines.values() for p in link.part_ids if p not in known.supply_parts]
    return issues
