"""Builds the SQL for one metric: a CTE that aggregates the metric's grain to the requested dimensions and period.

Joins follow declared many-to-one paths upward from the grain, so aggregation never double counts.
Values are always bound as parameters; identifiers are validated snake_case names, so no quoting is ever needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.enums import (
    Aggregation,
    FilterOperator,
    TimeAggregation,
    TimeGrain,
)
from supply_ontology.core.join_paths import resolve_join_path
from supply_ontology.core.metric_model import FilterValue, MeasureRef, Metric
from supply_ontology.core.query_spec import QuerySpec

PERIOD_COLUMN = "period"
NUMERATOR_SUFFIX = "__numerator"
DENOMINATOR_SUFFIX = "__denominator"
CTE_PREFIX = "m_"
SQL_OPERATOR = {FilterOperator.EQUALS: "=", FilterOperator.NOT_EQUALS: "<>",
                FilterOperator.IN: "IN", FilterOperator.NOT_IN: "NOT IN"}
INDENT = "    "


@dataclass
class Fragment:
    """SQL text with its positional parameters, in order."""

    sql: str
    parameters: list[object] = field(default_factory=list)


def period_expression(column: str, grain: TimeGrain | None) -> str | None:
    """Truncate a date column to the query's time grain."""
    if grain is None:
        return None
    return f"CAST(date_trunc('{grain.value}', {column}) AS DATE)"


def condition(column: str, operator: FilterOperator, values: tuple[FilterValue, ...]) -> Fragment:
    """A parameterised comparison."""
    if operator in (FilterOperator.IN, FilterOperator.NOT_IN):
        placeholders = ", ".join("?" for _ in values)
        return Fragment(f"{column} {SQL_OPERATOR[operator]} ({placeholders})", list(values))
    return Fragment(f"{column} {SQL_OPERATOR[operator]} ?", list(values))


def measure_expression(measure: MeasureRef, grain: str) -> str:
    """Aggregate expression for a numerator or denominator."""
    if measure.aggregation == Aggregation.COUNT:
        return "COUNT(*)"
    column = f"{grain}.{measure.attribute}"
    if measure.aggregation == Aggregation.COUNT_IF:
        return f"SUM(CASE WHEN {column} THEN 1 ELSE 0 END)"
    return f"SUM({column})"


def metric_cte(metric: Metric, spec: QuerySpec, catalog: SemanticCatalog, as_of: date) -> Fragment:
    """The full CTE body for one metric; rows attributed after `as_of` have no outcome yet and are excluded."""
    grain, time_column = metric.grain, f"{metric.grain}.{metric.time_dimension}"
    select = [f"{d.name} AS {d.alias}" for d in spec.dimensions]
    period = period_expression(time_column, spec.time_grain)
    if period is not None:
        select.append(f"{period} AS {PERIOD_COLUMN}")
    select.append(f"{measure_expression(metric.numerator, grain)} AS {metric.id}{NUMERATOR_SUFFIX}")
    if metric.denominator is not None:
        select.append(f"{measure_expression(metric.denominator, grain)} AS {metric.id}{DENOMINATOR_SUFFIX}")
    source = _grain_source(metric, spec, as_of)
    where = _where(metric, spec, as_of)
    group_by = [d.name for d in spec.dimensions] + ([period] if period is not None else [])
    lines = [f"SELECT {(',' + chr(10) + INDENT).join(select)}", f"FROM {source.sql}"]
    lines += _joins(metric, spec, catalog)
    if where.sql:
        lines.append(f"WHERE {where.sql}")
    if group_by:
        lines.append(f"GROUP BY {', '.join(group_by)}")
    return Fragment("\n".join(lines), source.parameters + where.parameters)


def _grain_source(metric: Metric, spec: QuerySpec, as_of: date) -> Fragment:
    """The grain table; period-end metrics keep only the last time value in each period."""
    grain, column = metric.grain, metric.time_dimension
    if metric.time_aggregation != TimeAggregation.PERIOD_END:
        return Fragment(grain)
    conditions = [Fragment(f"{column} IS NOT NULL"), Fragment(f"{column} <= ?", [as_of])]
    if spec.time_range is not None:
        conditions.append(Fragment(f"{column} BETWEEN ? AND ?", [spec.time_range.start, spec.time_range.end]))
    period = period_expression(column, spec.time_grain)
    partition = f"PARTITION BY {period}" if period is not None else ""
    sql = (f"(SELECT * FROM {grain} WHERE {' AND '.join(c.sql for c in conditions)} "
           f"QUALIFY {column} = max({column}) OVER ({partition})) AS {grain}")
    return Fragment(sql, [p for c in conditions for p in c.parameters])


def _joins(metric: Metric, spec: QuerySpec, catalog: SemanticCatalog) -> list[str]:
    targets = sorted({d.entity for d in spec.dimensions} | {f.dimension.entity for f in spec.filters})
    seen: list[str] = []
    joins = []
    for target in targets:
        for relationship in resolve_join_path(catalog.ontology, metric.grain, target):
            if relationship.name in seen:
                continue
            seen.append(relationship.name)
            on = " AND ".join(f"{relationship.from_entity}.{c} = {relationship.to_entity}.{p}" for c, p in relationship.join_columns)
            joins.append(f"LEFT JOIN {relationship.to_entity} ON {on}")
    return joins


def _where(metric: Metric, spec: QuerySpec, as_of: date) -> Fragment:
    time_column = f"{metric.grain}.{metric.time_dimension}"
    parts = [Fragment(f"{time_column} IS NOT NULL"), Fragment(f"{time_column} <= ?", [as_of])]
    parts += [condition(f"{metric.grain}.{f.attribute}", f.operator, f.values) for f in metric.filters]
    if spec.time_range is not None:
        parts.append(Fragment(f"{time_column} BETWEEN ? AND ?", [spec.time_range.start, spec.time_range.end]))
    parts += [condition(f.dimension.name, f.operator, f.values) for f in spec.filters]
    return Fragment(f"\n{INDENT}AND ".join(p.sql for p in parts), [v for p in parts for v in p.parameters])
