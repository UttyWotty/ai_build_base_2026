"""Semantic consistency checks for metric definitions against the ontology and against each other.

Per-metric checks cover grain, time dimension, aggregation-to-type compatibility, ratio shape, and filters.
Cross-metric checks enforce unique ids, valid not-to-be-confused-with references, and globally unique business terms.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from supply_ontology.core.enums import (
    NUMERIC_TYPES,
    SINGLE_VALUE_OPERATORS,
    Aggregation,
    AttributeType,
    MetricType,
)
from supply_ontology.core.errors import ValidationIssue
from supply_ontology.core.identifiers import IDENTIFIER_RULE, is_valid_identifier
from supply_ontology.core.metric_model import (
    MeasureRef,
    Metric,
    MetricFilter,
)
from supply_ontology.core.ontology_model import Entity, Ontology
from supply_ontology.core.terms import normalize_term
from supply_ontology.core.value_types import value_matches_type


def validate_metrics(metrics: Sequence[Metric], ontology: Ontology) -> list[ValidationIssue]:
    """Return every consistency problem across the metrics; an empty list means they are valid."""
    issues: list[ValidationIssue] = []
    for metric_id, count in sorted(Counter(m.id for m in metrics).items()):
        if count > 1:
            issues.append(ValidationIssue(f"metric {metric_id}", f"id is declared {count} times"))
    for metric in metrics:
        issues.extend(_check_metric(metric, ontology))
    issues.extend(_check_confusion_references(metrics))
    issues.extend(_check_term_collisions(metrics))
    return issues


def _location(metric: Metric) -> str:
    return f"metric {metric.id} ({metric.source})"


def _check_metric(metric: Metric, ontology: Ontology) -> list[ValidationIssue]:
    location = _location(metric)
    issues: list[ValidationIssue] = []
    if not is_valid_identifier(metric.id):
        issues.append(ValidationIssue(location, f"id {IDENTIFIER_RULE}"))
    grain = ontology.entity(metric.grain)
    if grain is None:
        return [*issues, ValidationIssue(location, f"grain entity '{metric.grain}' is not declared")]
    time_attribute = grain.attribute(metric.time_dimension)
    if time_attribute is None or time_attribute.data_type != AttributeType.DATE:
        issues.append(
            ValidationIssue(location, f"time_dimension '{metric.time_dimension}' must be a date attribute of '{grain.name}'")
        )
    issues.extend(_check_measure(metric.numerator, grain, f"{location} numerator"))
    issues.extend(_check_ratio_shape(metric, grain, location))
    for metric_filter in metric.filters:
        issues.extend(_check_filter(metric_filter, grain, f"{location} filter on '{metric_filter.attribute}'"))
    return issues


def _check_ratio_shape(metric: Metric, grain: Entity, location: str) -> list[ValidationIssue]:
    if metric.metric_type == MetricType.RATIO:
        if metric.denominator is None:
            return [ValidationIssue(location, "ratio metric requires a denominator")]
        return _check_measure(metric.denominator, grain, f"{location} denominator")
    if metric.denominator is not None:
        return [ValidationIssue(location, "simple metric must not declare a denominator")]
    return []


def _check_measure(measure: MeasureRef, grain: Entity, location: str) -> list[ValidationIssue]:
    if measure.aggregation == Aggregation.COUNT:
        if measure.attribute is not None:
            return [ValidationIssue(location, "count counts grain rows and takes no attribute")]
        return []
    if measure.attribute is None:
        return [ValidationIssue(location, f"{measure.aggregation.value} requires an attribute")]
    attribute = grain.attribute(measure.attribute)
    if attribute is None:
        return [ValidationIssue(location, f"'{measure.attribute}' is not an attribute of '{grain.name}'")]
    if measure.aggregation == Aggregation.SUM and attribute.data_type not in NUMERIC_TYPES:
        return [ValidationIssue(location, f"sum needs a numeric attribute; '{attribute.name}' is {attribute.data_type.value}")]
    if measure.aggregation == Aggregation.COUNT_IF and attribute.data_type != AttributeType.BOOLEAN:
        return [ValidationIssue(location, f"count_if needs a boolean attribute; '{attribute.name}' is {attribute.data_type.value}")]
    return []


def _check_filter(metric_filter: MetricFilter, grain: Entity, location: str) -> list[ValidationIssue]:
    attribute = grain.attribute(metric_filter.attribute)
    if attribute is None:
        return [ValidationIssue(location, f"'{metric_filter.attribute}' is not an attribute of '{grain.name}'")]
    issues: list[ValidationIssue] = []
    value_count = len(metric_filter.values)
    if metric_filter.operator in SINGLE_VALUE_OPERATORS and value_count != 1:
        issues.append(ValidationIssue(location, f"{metric_filter.operator.value} takes exactly one value"))
    if metric_filter.operator not in SINGLE_VALUE_OPERATORS and value_count == 0:
        issues.append(ValidationIssue(location, f"{metric_filter.operator.value} needs at least one value"))
    for value in metric_filter.values:
        if not value_matches_type(value, attribute.data_type):
            issues.append(ValidationIssue(location, f"value {value!r} does not match type {attribute.data_type.value}"))
    return issues


def _check_confusion_references(metrics: Sequence[Metric]) -> list[ValidationIssue]:
    known = {metric.id for metric in metrics}
    issues: list[ValidationIssue] = []
    for metric in metrics:
        for other in metric.not_to_be_confused_with:
            if other == metric.id:
                issues.append(ValidationIssue(_location(metric), "lists itself in not_to_be_confused_with"))
            elif other not in known:
                issues.append(ValidationIssue(_location(metric), f"not_to_be_confused_with names unknown metric '{other}'"))
    return issues


def _check_term_collisions(metrics: Sequence[Metric]) -> list[ValidationIssue]:
    """Every business term (id, label, synonym) must resolve to exactly one metric."""
    owner_of: dict[str, str] = {}
    issues: list[ValidationIssue] = []
    for metric in metrics:
        for term in {normalize_term(t) for t in (metric.id, metric.label, *metric.synonyms)}:
            previous = owner_of.setdefault(term, metric.id)
            if previous != metric.id:
                issues.append(
                    ValidationIssue(_location(metric), f"term '{term}' already resolves to metric '{previous}'")
                )
    return issues
