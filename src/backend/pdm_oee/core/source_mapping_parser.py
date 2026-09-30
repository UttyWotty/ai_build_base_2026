"""Parses the source mappings document into SourceMappings.

Shape errors name the dotted path of the offending field; unknown fields are rejected to catch typos.
Whether the mappings cover every governed reason and failure mode is checked by the source mapping validator.
"""
from __future__ import annotations

from pdm_oee.core.enums import MachineState, SensorUnit, WorkType
from pdm_oee.core.errors import SemanticParseError
from pdm_oee.core.field_readers import (
    RawMapping,
    as_mapping,
    as_str,
    join_path,
    reject_unknown_keys,
    require_enum,
    require_mapping,
    require_positive_number,
    require_str,
    require_str_list,
)
from pdm_oee.core.source_mapping_model import (
    CmmsMapping,
    PrintedUnit,
    SiteMapping,
    SourceMappings,
)

ROOT_KEYS = frozenset({"sites", "printed_units", "cmms"})
SITE_KEYS = frozenset({"number", "timezone", "quality", "states", "reasons"})
QUALITY_KEYS = frozenset({"good", "bad"})
UNIT_KEYS = frozenset({"unit", "offset", "scale"})
CMMS_KEYS = frozenset({"work_types", "failure_codes", "failure_keywords"})


def parse_source_mappings(raw: object) -> SourceMappings:
    root = as_mapping(raw, "source_mappings")
    reject_unknown_keys(root, ROOT_KEYS, "source_mappings")
    sites = {name: _site(name, as_mapping(v, f"sites.{name}")) for name, v in require_mapping(root, "sites", "").items()}
    units = {text: _unit(text, as_mapping(v, f"printed_units.{text}")) for text, v in require_mapping(root, "printed_units", "").items()}
    return SourceMappings(sites, units, _cmms(require_mapping(root, "cmms", "")))


def _site(name: str, raw: RawMapping) -> SiteMapping:
    path = f"sites.{name}"
    reject_unknown_keys(raw, SITE_KEYS, path)
    number = raw.get("number")
    if isinstance(number, bool) or not isinstance(number, int):
        raise SemanticParseError(join_path(path, "number"), "expected an integer")
    quality = require_mapping(raw, "quality", path)
    reject_unknown_keys(quality, QUALITY_KEYS, join_path(path, "quality"))
    states = {code: _enum(value, f"{path}.states.{code}", MachineState) for code, value in require_mapping(raw, "states", path).items()}
    reasons = {code: as_str(value, f"{path}.reasons.{code}") for code, value in require_mapping(raw, "reasons", path).items()}
    return SiteMapping(name, number, require_str(raw, "timezone", path),
                       require_str_list(quality, "good", join_path(path, "quality")),
                       require_str_list(quality, "bad", join_path(path, "quality")), states, reasons)


def _unit(text: str, raw: RawMapping) -> PrintedUnit:
    path = f"printed_units.{text}"
    reject_unknown_keys(raw, UNIT_KEYS, path)
    offset = raw.get("offset", 0)
    if isinstance(offset, bool) or not isinstance(offset, (int, float)):
        raise SemanticParseError(join_path(path, "offset"), "expected a number")
    return PrintedUnit(text, require_enum(raw, "unit", path, SensorUnit), float(offset), require_positive_number(raw, "scale", path))


def _cmms(raw: RawMapping) -> CmmsMapping:
    reject_unknown_keys(raw, CMMS_KEYS, "cmms")
    work_types = {code: _enum(v, f"cmms.work_types.{code}", WorkType) for code, v in require_mapping(raw, "work_types", "cmms").items()}
    codes = {code: as_str(v, f"cmms.failure_codes.{code}") for code, v in require_mapping(raw, "failure_codes", "cmms").items()}
    keywords_raw = require_mapping(raw, "failure_keywords", "cmms")
    keywords = {mode: require_str_list(keywords_raw, mode, "cmms.failure_keywords") for mode in keywords_raw}
    return CmmsMapping(work_types, codes, keywords)


def _enum(value: object, path: str, enum_type: type) -> object:
    text = as_str(value, path)
    try:
        return enum_type(text)
    except ValueError:
        allowed = ", ".join(member.value for member in enum_type)
        raise SemanticParseError(path, f"'{text}' is not one of: {allowed}") from None
