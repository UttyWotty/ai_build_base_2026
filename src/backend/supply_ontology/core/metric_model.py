"""Immutable data model for governed metric definitions.

A metric fixes its grain, time attribution, aggregation, filters, and synonyms so it can only be computed one way.
Instances are produced by the metric parser and checked against the ontology by the metric validator.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from supply_ontology.core.enums import (
    Aggregation,
    FilterOperator,
    MetricFormat,
    MetricType,
    Team,
    TimeAggregation,
)

FilterValue = str | int | float | bool
ParameterValue = int | float


@dataclass(frozen=True)
class MeasureRef:
    """An aggregation over one attribute of the grain entity (no attribute for COUNT)."""

    aggregation: Aggregation
    attribute: str | None


@dataclass(frozen=True)
class MetricFilter:
    """A fixed filter that is part of the metric's definition, not a user choice."""

    attribute: str
    operator: FilterOperator
    values: tuple[FilterValue, ...]


@dataclass(frozen=True)
class Metric:
    """A canonical or declared-variant metric with exactly one computation."""

    id: str
    label: str
    description: str
    owner: Team
    metric_type: MetricType
    grain: str
    time_dimension: str
    time_aggregation: TimeAggregation
    numerator: MeasureRef
    denominator: MeasureRef | None
    filters: tuple[MetricFilter, ...]
    value_format: MetricFormat
    parameters: Mapping[str, ParameterValue]
    synonyms: tuple[str, ...]
    not_to_be_confused_with: tuple[str, ...]
    source: str
