"""Checks the source mappings against the governed catalog, so conform can never meet an unplanned case silently.

Every site maps every governed stop reason and every machine state; quality codes are unambiguous; every canonical
sensor unit can be reached; every failure mode has a CMMS code and keywords that cannot match another mode of its class.
"""
from __future__ import annotations

from collections import Counter

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import MachineState, SensorUnit, WorkType
from pdm_oee.core.errors import ValidationIssue
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.core.terms import normalize_text


def validate_source_mappings(mappings: SourceMappings, catalog: PlantCatalog) -> list[ValidationIssue]:
    issues = []
    reasons = {*catalog.losses.planned_stop_reasons, *catalog.losses.loss_reasons}
    for site in mappings.sites.values():
        at = f"sites.{site.site_id}"
        mapped = Counter(site.reasons.values())
        issues += [ValidationIssue(at, f"reason '{r}' is not mapped") for r in sorted(reasons - set(mapped))]
        issues += [ValidationIssue(at, f"'{r}' is not a governed stop reason") for r in sorted(set(mapped) - reasons)]
        issues += [ValidationIssue(at, f"reason '{r}' is mapped by {n} codes") for r, n in sorted(mapped.items()) if n > 1]
        missing_states = set(MachineState) - set(site.states.values())
        issues += [ValidationIssue(at, f"state '{s.value}' is not mapped") for s in sorted(missing_states, key=lambda s: s.value)]
        if not site.good_quality or not site.bad_quality or set(site.good_quality) & set(site.bad_quality):
            issues.append(ValidationIssue(at, "quality codes must be non-empty and good and bad must not overlap"))
    numbers = Counter(site.number for site in mappings.sites.values())
    issues += [ValidationIssue("sites", f"site number {n} is used twice") for n, c in numbers.items() if c > 1]
    reached = {unit.unit for unit in mappings.printed_units.values()}
    issues += [ValidationIssue("printed_units", f"no printed unit converts to {u.value}") for u in SensorUnit if u not in reached]
    return issues + _check_cmms(mappings, catalog)


def _check_cmms(mappings: SourceMappings, catalog: PlantCatalog) -> list[ValidationIssue]:
    cmms, issues = mappings.cmms, []
    missing_types = set(WorkType) - set(cmms.work_types.values())
    issues += [ValidationIssue("cmms.work_types", f"'{t.value}' has no code") for t in sorted(missing_types, key=lambda t: t.value)]
    modes = {m for c in catalog.plant.asset_classes.values() for m in c.failure_modes}
    coded = set(cmms.failure_codes.values())
    issues += [ValidationIssue("cmms.failure_codes", f"'{m}' is not a failure mode") for m in sorted(coded - modes)]
    issues += [ValidationIssue("cmms.failure_codes", f"'{m}' has no code") for m in sorted(modes - coded)]
    issues += [ValidationIssue("cmms.failure_keywords", f"'{m}' has no keywords") for m in sorted(modes - set(cmms.failure_keywords))]
    for asset_class in catalog.plant.asset_classes.values():
        for mode in asset_class.failure_modes:
            for keyword in cmms.failure_keywords.get(mode, ()):
                clashes = [other for other in asset_class.failure_modes if other != mode and any(
                    normalize_text(keyword) in normalize_text(k) for k in cmms.failure_keywords.get(other, ()))]
                issues += [ValidationIssue(f"cmms.failure_keywords.{mode}", f"'{keyword}' also matches '{c}'") for c in clashes]
    return issues
