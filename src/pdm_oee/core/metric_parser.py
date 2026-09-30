"""Parses the measures document and the metric documents into Measure and Metric records.

Shape errors name the dotted path (and, for metrics, the file) of the offending field.
Whether measures exist and fit together is checked by the metric validator.
"""
from __future__ import annotations

from pdm_oee.core.enums import Grain, MeasureUnit, MetricFormat, Team
from pdm_oee.core.field_readers import (
    as_mapping,
    optional_number_map,
    optional_str_list,
    reject_unknown_keys,
    require_enum,
    require_mapping,
    require_str,
)
from pdm_oee.core.metric_model import Measure, Metric

MEASURE_KEYS = frozenset({"label", "grain", "unit", "definition", "parameters"})
METRIC_KEYS = frozenset({"id", "label", "description", "owner", "numerator", "denominator", "format",
                         "synonyms", "not_to_be_confused_with"})


def parse_measures(raw: object) -> dict[str, Measure]:
    """Turn the measures document into measures keyed by id."""
    root = as_mapping(raw, "measures")
    reject_unknown_keys(root, frozenset({"measures"}), "measures")
    measures = {}
    for name, value in require_mapping(root, "measures", "").items():
        path = f"measures.{name}"
        fields = as_mapping(value, path)
        reject_unknown_keys(fields, MEASURE_KEYS, path)
        measures[name] = Measure(
            id=name, label=require_str(fields, "label", path), grain=require_enum(fields, "grain", path, Grain),
            unit=require_enum(fields, "unit", path, MeasureUnit), definition=require_str(fields, "definition", path),
            parameters=optional_number_map(fields, "parameters", path),
        )
    return measures


def parse_metric(raw: object, source: str) -> Metric:
    """Turn one metric document into a Metric; `source` is its file name, used in error paths."""
    fields = as_mapping(raw, source)
    reject_unknown_keys(fields, METRIC_KEYS, source)
    return Metric(
        id=require_str(fields, "id", source), label=require_str(fields, "label", source),
        description=require_str(fields, "description", source), owner=require_enum(fields, "owner", source, Team),
        numerator=require_str(fields, "numerator", source), denominator=require_str(fields, "denominator", source),
        value_format=require_enum(fields, "format", source, MetricFormat),
        synonyms=optional_str_list(fields, "synonyms", source),
        not_to_be_confused_with=optional_str_list(fields, "not_to_be_confused_with", source),
        source=source,
    )
