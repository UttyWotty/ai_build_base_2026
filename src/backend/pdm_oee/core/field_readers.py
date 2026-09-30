"""Typed readers that pull fields out of raw YAML-derived mappings with precise error paths.

Every reader either returns a value of the declared type or raises SemanticParseError naming the offending path.
Parsers use these readers so that shape errors in the semantic files are reported consistently.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TypeVar, cast

from pdm_oee.core.errors import SemanticParseError

EnumT = TypeVar("EnumT", bound=Enum)
RawMapping = Mapping[str, object]

EMPTY_MAPPING: RawMapping = {}
EMPTY_LIST: tuple[object, ...] = ()
EMPTY_STRINGS: tuple[str, ...] = ()


def join_path(parent: str, child: str) -> str:
    """Append a child field name to a dotted error path."""
    return f"{parent}.{child}" if parent else child


def as_mapping(value: object, path: str) -> RawMapping:
    """Return the value as a string-keyed mapping, or fail."""
    if not isinstance(value, Mapping):
        raise SemanticParseError(path, "expected a mapping")
    for key in value:
        if not isinstance(key, str):
            raise SemanticParseError(path, f"key {key!r} is not a string")
    return cast(RawMapping, value)


def as_list(value: object, path: str) -> list[object]:
    """Return the value as a list, or fail."""
    if not isinstance(value, list):
        raise SemanticParseError(path, "expected a list")
    return value


def as_str(value: object, path: str) -> str:
    """Return the value as a non-blank string, or fail."""
    if not isinstance(value, str) or not value.strip():
        raise SemanticParseError(path, "expected a non-empty string")
    return value


def reject_unknown_keys(raw: RawMapping, allowed: frozenset[str], path: str) -> None:
    """Fail on any key outside the allowed set, which catches misspelled fields."""
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise SemanticParseError(path, f"unknown field(s): {', '.join(unknown)}")


def require_value(raw: RawMapping, key: str, path: str) -> object:
    """Return a required field's raw value, or fail when it is absent."""
    if key not in raw:
        raise SemanticParseError(join_path(path, key), "is required")
    return raw[key]


def require_str(raw: RawMapping, key: str, path: str) -> str:
    """Return a required non-blank string field."""
    return as_str(require_value(raw, key, path), join_path(path, key))


def optional_str(raw: RawMapping, key: str, path: str) -> str | None:
    """Return an optional string field; an absent field yields None."""
    if key not in raw:
        return None
    return as_str(raw[key], join_path(path, key))


def optional_bool(raw: RawMapping, key: str, path: str, default: bool) -> bool:
    """Return an optional boolean field, using the caller's explicit default when absent."""
    if key not in raw:
        return default
    value = raw[key]
    if not isinstance(value, bool):
        raise SemanticParseError(join_path(path, key), "expected true or false")
    return value


def require_mapping(raw: RawMapping, key: str, path: str) -> RawMapping:
    """Return a required mapping field."""
    return as_mapping(require_value(raw, key, path), join_path(path, key))


def optional_mapping(raw: RawMapping, key: str, path: str) -> RawMapping:
    """Return an optional mapping field; an absent field yields an empty mapping."""
    if key not in raw:
        return EMPTY_MAPPING
    return as_mapping(raw[key], join_path(path, key))


def optional_list(raw: RawMapping, key: str, path: str) -> list[object]:
    """Return an optional list field; an absent field yields an empty list."""
    if key not in raw:
        return list(EMPTY_LIST)
    return as_list(raw[key], join_path(path, key))


def require_str_list(raw: RawMapping, key: str, path: str) -> tuple[str, ...]:
    """Return a required list of non-blank strings."""
    field_path = join_path(path, key)
    items = as_list(require_value(raw, key, path), field_path)
    return tuple(as_str(item, f"{field_path}[{index}]") for index, item in enumerate(items))


def optional_str_list(raw: RawMapping, key: str, path: str) -> tuple[str, ...]:
    """Return an optional list of non-blank strings; an absent field yields an empty tuple."""
    if key not in raw:
        return EMPTY_STRINGS
    return require_str_list(raw, key, path)


def require_enum(raw: RawMapping, key: str, path: str, enum_type: type[EnumT]) -> EnumT:
    """Return a required field converted to a member of the given enum."""
    text = require_str(raw, key, path)
    try:
        return enum_type(text)
    except ValueError:
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise SemanticParseError(
            join_path(path, key), f"'{text}' is not one of: {allowed}"
        ) from None


def optional_enum(
    raw: RawMapping, key: str, path: str, enum_type: type[EnumT], default: EnumT
) -> EnumT:
    """Return an optional enum field, using the caller's explicit default when absent."""
    if key not in raw:
        return default
    return require_enum(raw, key, path, enum_type)


def require_positive_number(raw: RawMapping, key: str, path: str) -> float:
    """Return a required number greater than zero (booleans are rejected)."""
    value = require_value(raw, key, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise SemanticParseError(join_path(path, key), "expected a number greater than zero")
    return float(value)


def require_number_pair(raw: RawMapping, key: str, path: str) -> tuple[float, float]:
    """Return a required two-number list such as a [low, high] range."""
    field_path = join_path(path, key)
    items = as_list(require_value(raw, key, path), field_path)
    if len(items) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in items):
        raise SemanticParseError(field_path, "expected a list of two numbers")
    return float(items[0]), float(items[1])


def optional_number_map(raw: RawMapping, key: str, path: str) -> dict[str, float]:
    """Return an optional mapping of names to numbers; an absent field yields an empty mapping."""
    field_path = join_path(path, key)
    result = {}
    for name, value in optional_mapping(raw, key, path).items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SemanticParseError(join_path(field_path, name), "expected a number")
        result[name] = float(value)
    return result
