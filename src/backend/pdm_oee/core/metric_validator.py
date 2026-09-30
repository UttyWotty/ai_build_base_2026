"""Consistency checks for measures and metrics: references, grains, units against formats, terms, and look-alikes.

A percent needs numerator and denominator in the same unit; an hours metric needs hours over a count.
Every business term (id, label, synonym) resolves to exactly one metric, and look-alike declarations must be mutual.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from pdm_oee.core.enums import MeasureUnit, MetricFormat
from pdm_oee.core.errors import ValidationIssue
from pdm_oee.core.identifiers import IDENTIFIER_RULE, is_valid_identifier
from pdm_oee.core.metric_model import Measure, Metric
from pdm_oee.core.terms import normalize_term


def validate_metrics(measures: Mapping[str, Measure], metrics: Sequence[Metric]) -> list[ValidationIssue]:
    """Every problem in the measures and metrics."""
    issues = [ValidationIssue(f"measures.{m}", f"name {IDENTIFIER_RULE}") for m in measures if not is_valid_identifier(m)]
    seen: dict[str, str] = {}
    for metric in metrics:
        if not is_valid_identifier(metric.id):
            issues.append(ValidationIssue(metric.source, f"id '{metric.id}' {IDENTIFIER_RULE}"))
        if metric.id in seen:
            issues.append(ValidationIssue(metric.source, f"id '{metric.id}' is already defined in {seen[metric.id]}"))
        seen.setdefault(metric.id, metric.source)
        issues += _check_ratio(metric, measures)
    return issues + _check_terms(metrics) + _check_look_alikes(metrics)


def _check_ratio(metric: Metric, measures: Mapping[str, Measure]) -> list[ValidationIssue]:
    missing = [m for m in (metric.numerator, metric.denominator) if m not in measures]
    if missing:
        return [ValidationIssue(metric.source, f"unknown measure(s): {', '.join(missing)}")]
    top, bottom = measures[metric.numerator], measures[metric.denominator]
    issues = []
    if top.id == bottom.id:
        issues.append(ValidationIssue(metric.source, "numerator and denominator must differ"))
    if top.grain is not bottom.grain:
        issues.append(ValidationIssue(metric.source, f"numerator grain {top.grain.value} differs from denominator grain {bottom.grain.value}"))
    if metric.value_format is MetricFormat.PERCENT and top.unit is not bottom.unit:
        issues.append(ValidationIssue(metric.source, f"a percent needs one unit, not {top.unit.value} over {bottom.unit.value}"))
    if metric.value_format is MetricFormat.HOURS and (top.unit, bottom.unit) != (MeasureUnit.HOURS, MeasureUnit.COUNT):
        issues.append(ValidationIssue(metric.source, f"an hours metric needs hours over a count, not {top.unit.value} over {bottom.unit.value}"))
    return issues


def _check_terms(metrics: Sequence[Metric]) -> list[ValidationIssue]:
    owners: dict[str, str] = {}
    issues = []
    for metric in metrics:
        for term in {normalize_term(t) for t in (metric.id, metric.label, *metric.synonyms)}:
            other = owners.setdefault(term, metric.id)
            if other != metric.id:
                issues.append(ValidationIssue(metric.source, f"term '{term}' already belongs to metric '{other}'"))
    return issues


def _check_look_alikes(metrics: Sequence[Metric]) -> list[ValidationIssue]:
    declared = {m.id: set(m.not_to_be_confused_with) for m in metrics}
    issues = []
    for metric in metrics:
        for other in metric.not_to_be_confused_with:
            if other == metric.id:
                issues.append(ValidationIssue(metric.source, "a metric cannot be its own look-alike"))
            elif other not in declared:
                issues.append(ValidationIssue(metric.source, f"look-alike '{other}' is not a defined metric"))
            elif metric.id not in declared[other]:
                issues.append(ValidationIssue(metric.source, f"'{other}' must also list '{metric.id}' as a look-alike"))
    return issues
