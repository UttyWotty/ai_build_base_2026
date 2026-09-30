"""Checks a parsed query spec against the catalog before compilation.

Every metric must exist, and every dimension and filter must be an attribute reachable from every requested metric's grain.
Issues are phrased so they can be shown to a user or fed back to the language model for a corrected attempt.
"""
from __future__ import annotations

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.enums import SINGLE_VALUE_OPERATORS
from supply_ontology.core.errors import JoinPathError, ValidationIssue
from supply_ontology.core.join_paths import resolve_join_path
from supply_ontology.core.query_spec import DimensionRef, QueryFilter, QuerySpec
from supply_ontology.core.value_types import value_matches_type

LOCATION = "query"


def validate_query(spec: QuerySpec, catalog: SemanticCatalog) -> list[ValidationIssue]:
    """Return every problem with the spec; an empty list means it can be compiled."""
    issues = _check_metrics(spec, catalog)
    grains = [catalog.metrics[m].grain for m in spec.metrics if m in catalog.metrics]
    if len({d.name for d in spec.dimensions}) != len(spec.dimensions):
        issues.append(ValidationIssue(LOCATION, "dimensions must not repeat"))
    for dimension in spec.dimensions:
        issues.extend(_check_dimension(dimension, grains, catalog))
    for query_filter in spec.filters:
        issues.extend(_check_filter(query_filter, grains, catalog))
    if spec.time_range is not None and spec.time_range.start > spec.time_range.end:
        issues.append(ValidationIssue(LOCATION, "time_range start is after its end"))
    return issues


def _check_metrics(spec: QuerySpec, catalog: SemanticCatalog) -> list[ValidationIssue]:
    issues = []
    if not spec.metrics:
        issues.append(ValidationIssue(LOCATION, "at least one metric is required"))
    if len(set(spec.metrics)) != len(spec.metrics):
        issues.append(ValidationIssue(LOCATION, "metrics must not repeat"))
    known = ", ".join(sorted(catalog.metrics))
    for metric_id in spec.metrics:
        if metric_id not in catalog.metrics:
            issues.append(ValidationIssue(LOCATION, f"unknown metric '{metric_id}'; choose from: {known}"))
    return issues


def _check_dimension(dimension: DimensionRef, grains: list[str], catalog: SemanticCatalog) -> list[ValidationIssue]:
    entity = catalog.ontology.entity(dimension.entity)
    if entity is None:
        return [ValidationIssue(LOCATION, f"unknown entity '{dimension.entity}' in '{dimension.name}'")]
    if entity.attribute(dimension.attribute) is None:
        return [ValidationIssue(LOCATION, f"'{dimension.attribute}' is not an attribute of '{entity.name}'")]
    issues = []
    for grain in grains:
        try:
            resolve_join_path(catalog.ontology, grain, dimension.entity)
        except JoinPathError:
            issues.append(ValidationIssue(LOCATION, f"'{dimension.name}' cannot be reached from grain '{grain}'"))
    return issues


def _check_filter(query_filter: QueryFilter, grains: list[str], catalog: SemanticCatalog) -> list[ValidationIssue]:
    issues = _check_dimension(query_filter.dimension, grains, catalog)
    if issues:
        return issues
    name = query_filter.dimension.name
    count = len(query_filter.values)
    if query_filter.operator in SINGLE_VALUE_OPERATORS and count != 1:
        issues.append(ValidationIssue(LOCATION, f"filter on '{name}': {query_filter.operator.value} takes exactly one value"))
    if count == 0:
        issues.append(ValidationIssue(LOCATION, f"filter on '{name}' needs at least one value"))
    attribute = catalog.ontology.entities[query_filter.dimension.entity].attributes[query_filter.dimension.attribute]
    for value in query_filter.values:
        if not value_matches_type(value, attribute.data_type):
            issues.append(ValidationIssue(LOCATION, f"filter on '{name}': value {value!r} is not a {attribute.data_type.value}"))
    return issues
