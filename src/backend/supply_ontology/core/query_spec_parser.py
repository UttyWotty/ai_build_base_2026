"""Parses a raw (JSON-derived) query spec into a QuerySpec, checking shape only.

Whether metrics and dimensions exist, and whether dimensions are reachable, is the query validator's job.
Errors carry the dotted path of the offending field so they can be fed back to the language model verbatim.
"""
from __future__ import annotations

from datetime import date

from supply_ontology.core.enums import FilterOperator, TimeGrain
from supply_ontology.core.errors import SemanticParseError
from supply_ontology.core.field_readers import (
    RawMapping,
    as_mapping,
    as_str,
    join_path,
    optional_list,
    reject_unknown_keys,
    require_enum,
    require_str,
    require_str_list,
    require_value,
)
from supply_ontology.core.metric_model import FilterValue
from supply_ontology.core.query_spec import (
    DIMENSION_SEPARATOR,
    DimensionRef,
    QueryFilter,
    QuerySpec,
    TimeRange,
)

ROOT_PATH = "query"
SPEC_KEYS = frozenset({"metrics", "dimensions", "filters", "time_range", "time_grain"})
FILTER_KEYS = frozenset({"dimension", "operator", "value"})
RANGE_KEYS = frozenset({"start", "end"})


def parse_dimension(text: str, path: str) -> DimensionRef:
    """Parse entity.attribute."""
    entity, separator, attribute = text.partition(DIMENSION_SEPARATOR)
    if not separator or not entity or not attribute:
        raise SemanticParseError(path, f"'{text}' must be written entity.attribute")
    return DimensionRef(entity=entity, attribute=attribute)


def parse_query_spec(raw: object) -> QuerySpec:
    """Parse a whole query spec document."""
    fields = as_mapping(raw, ROOT_PATH)
    reject_unknown_keys(fields, SPEC_KEYS, ROOT_PATH)
    dimensions_path = join_path(ROOT_PATH, "dimensions")
    dimension_texts = [as_str(d, f"{dimensions_path}[{i}]") for i, d in enumerate(optional_list(fields, "dimensions", ROOT_PATH))]
    filters_path = join_path(ROOT_PATH, "filters")
    return QuerySpec(
        metrics=require_str_list(fields, "metrics", ROOT_PATH),
        dimensions=tuple(parse_dimension(t, f"{dimensions_path}[{i}]") for i, t in enumerate(dimension_texts)),
        filters=tuple(_parse_filter(f, f"{filters_path}[{i}]") for i, f in enumerate(optional_list(fields, "filters", ROOT_PATH))),
        time_range=_parse_range(fields.get("time_range"), join_path(ROOT_PATH, "time_range")),
        time_grain=None if fields.get("time_grain") is None else require_enum(fields, "time_grain", ROOT_PATH, TimeGrain),
    )


def _parse_filter(raw: object, path: str) -> QueryFilter:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, FILTER_KEYS, path)
    value = require_value(fields, "value", path)
    values = value if isinstance(value, list) else [value]
    for index, item in enumerate(values):
        if not isinstance(item, (str, int, float, bool)):
            raise SemanticParseError(f"{join_path(path, 'value')}[{index}]", "expected a string, number, or boolean")
    typed: tuple[FilterValue, ...] = tuple(values)
    return QueryFilter(
        dimension=parse_dimension(require_str(fields, "dimension", path), join_path(path, "dimension")),
        operator=require_enum(fields, "operator", path, FilterOperator),
        values=typed,
    )


def _parse_range(raw: object, path: str) -> TimeRange | None:
    if raw is None:
        return None
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, RANGE_KEYS, path)
    return TimeRange(start=_parse_date(fields, "start", path), end=_parse_date(fields, "end", path))


def _parse_date(fields: RawMapping, key: str, path: str) -> date:
    value = require_value(fields, key, path)
    if isinstance(value, date):
        return value
    text = as_str(value, join_path(path, key))
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise SemanticParseError(join_path(path, key), f"'{text}' is not an ISO date (YYYY-MM-DD)") from None
