"""Converts one raw metric document (loaded from YAML) into the immutable metric model.

The parser checks shape only: required fields, field types, enum values, and unknown keys.
Whether the referenced grain, attributes, and related metrics exist is checked later by the metric validator.
"""
from __future__ import annotations

from supply_ontology.core.enums import (
    Aggregation,
    FilterOperator,
    MetricFormat,
    MetricType,
    Team,
    TimeAggregation,
)
from supply_ontology.core.errors import SemanticParseError
from supply_ontology.core.field_readers import (
    as_mapping,
    join_path,
    optional_enum,
    optional_list,
    optional_mapping,
    optional_str,
    optional_str_list,
    reject_unknown_keys,
    require_enum,
    require_str,
    require_value,
)
from supply_ontology.core.metric_model import (
    FilterValue,
    MeasureRef,
    Metric,
    MetricFilter,
    ParameterValue,
)

METRIC_KEYS = frozenset(
    {
        "id", "label", "description", "owner", "type", "grain", "time_dimension",
        "time_aggregation", "numerator", "denominator", "filters", "format",
        "parameters", "synonyms", "not_to_be_confused_with",
    }
)
MEASURE_KEYS = frozenset({"aggregation", "attribute"})
FILTER_KEYS = frozenset({"attribute", "operator", "value"})

# Most metrics sum across the period; snapshot metrics must opt in to period_end explicitly.
DEFAULT_TIME_AGGREGATION = TimeAggregation.ADDITIVE


def parse_metric(raw: object, source: str) -> Metric:
    """Parse one metric document; `source` names the file for error messages."""
    fields = as_mapping(raw, source)
    reject_unknown_keys(fields, METRIC_KEYS, source)
    denominator = (
        _parse_measure(fields["denominator"], join_path(source, "denominator"))
        if "denominator" in fields
        else None
    )
    return Metric(
        id=require_str(fields, "id", source),
        label=require_str(fields, "label", source),
        description=require_str(fields, "description", source),
        owner=require_enum(fields, "owner", source, Team),
        metric_type=require_enum(fields, "type", source, MetricType),
        grain=require_str(fields, "grain", source),
        time_dimension=require_str(fields, "time_dimension", source),
        time_aggregation=optional_enum(
            fields, "time_aggregation", source, TimeAggregation, DEFAULT_TIME_AGGREGATION
        ),
        numerator=_parse_measure(
            require_value(fields, "numerator", source), join_path(source, "numerator")
        ),
        denominator=denominator,
        filters=_parse_filters(optional_list(fields, "filters", source), source),
        value_format=require_enum(fields, "format", source, MetricFormat),
        parameters=_parse_parameters(optional_mapping(fields, "parameters", source), source),
        synonyms=optional_str_list(fields, "synonyms", source),
        not_to_be_confused_with=optional_str_list(fields, "not_to_be_confused_with", source),
        source=source,
    )


def _parse_measure(raw: object, path: str) -> MeasureRef:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, MEASURE_KEYS, path)
    return MeasureRef(
        aggregation=require_enum(fields, "aggregation", path, Aggregation),
        attribute=optional_str(fields, "attribute", path),
    )


def _parse_filters(items: list[object], source: str) -> tuple[MetricFilter, ...]:
    filters_path = join_path(source, "filters")
    parsed: list[MetricFilter] = []
    for index, item in enumerate(items):
        path = f"{filters_path}[{index}]"
        fields = as_mapping(item, path)
        reject_unknown_keys(fields, FILTER_KEYS, path)
        parsed.append(
            MetricFilter(
                attribute=require_str(fields, "attribute", path),
                operator=require_enum(fields, "operator", path, FilterOperator),
                values=_as_filter_values(
                    require_value(fields, "value", path), join_path(path, "value")
                ),
            )
        )
    return tuple(parsed)


def _as_filter_values(value: object, path: str) -> tuple[FilterValue, ...]:
    items = value if isinstance(value, list) else [value]
    for index, item in enumerate(items):
        if not isinstance(item, (str, int, float, bool)):
            raise SemanticParseError(
                f"{path}[{index}]", "expected a string, number, or boolean (quote dates)"
            )
    return tuple(items)


def _parse_parameters(raw: object, source: str) -> dict[str, ParameterValue]:
    path = join_path(source, "parameters")
    parameters: dict[str, ParameterValue] = {}
    for name, value in as_mapping(raw, path).items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SemanticParseError(join_path(path, name), "expected a number")
        parameters[name] = value
    return parameters
