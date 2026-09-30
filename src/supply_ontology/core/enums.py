"""Closed vocabularies used by the ontology and metric definitions.

Every enumerated value that appears in the semantic YAML files is declared here, so parsers can reject typos.
Grouped type sets (such as numeric attribute types) live next to the enums they classify.
"""
from __future__ import annotations

from enum import Enum


class AttributeType(str, Enum):
    """Logical data type of an entity attribute."""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    BOOLEAN = "boolean"


NUMERIC_TYPES: frozenset[AttributeType] = frozenset(
    {AttributeType.INTEGER, AttributeType.DECIMAL}
)


class Cardinality(str, Enum):
    """Direction-aware cardinality of a relationship, read from child to parent."""

    MANY_TO_ONE = "many_to_one"
    ONE_TO_ONE = "one_to_one"


class Aggregation(str, Enum):
    """How a measure is aggregated at the metric's grain."""

    SUM = "sum"
    COUNT = "count"
    COUNT_IF = "count_if"


class MetricType(str, Enum):
    """Whether a metric is a single aggregate or a numerator over a denominator."""

    SIMPLE = "simple"
    RATIO = "ratio"


class TimeAggregation(str, Enum):
    """How a metric rolls up over time: summed across the period, or taken at period end."""

    ADDITIVE = "additive"
    PERIOD_END = "period_end"


class MetricFormat(str, Enum):
    """Presentation format of a metric value."""

    PERCENT = "percent"
    CURRENCY_USD = "currency_usd"
    DAYS = "days"
    NUMBER = "number"


class FilterOperator(str, Enum):
    """Comparison operators allowed in governed metric filters."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"


SINGLE_VALUE_OPERATORS: frozenset[FilterOperator] = frozenset(
    {FilterOperator.EQUALS, FilterOperator.NOT_EQUALS}
)


class Team(str, Enum):
    """Business teams that own metrics and act as query personas."""

    PLANNING = "planning"
    PROCUREMENT = "procurement"
    LOGISTICS = "logistics"


class TimeGrain(str, Enum):
    """Calendar buckets a query can group a metric's time dimension into."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
