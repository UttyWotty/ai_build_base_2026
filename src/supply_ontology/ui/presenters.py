"""Pure formatting for the UI: metric values, metric definitions, result tables, and clarification follow-ups.

Nothing here imports Streamlit, so every rule is unit tested.
Definitions are shown exactly as the catalog states them, because showing which definition answered is the point of the UI.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.enums import MetricFormat
from supply_ontology.core.metric_model import MeasureRef, Metric

PERCENT = 100
MISSING_VALUE = "no value"
LIST_SEPARATOR = ", "
NONE_LISTED = "none"


def format_value(value: object, value_format: MetricFormat) -> str:
    """A metric value as people read it: 78.4%, $12.35, 23.5 days."""
    if value is None or pd.isna(value):
        return MISSING_VALUE
    number = float(value)
    if value_format is MetricFormat.PERCENT:
        return f"{number * PERCENT:.1f}%"
    if value_format is MetricFormat.CURRENCY_USD:
        return f"${number:,.2f}"
    if value_format is MetricFormat.DAYS:
        return f"{number:,.1f} days"
    return f"{number:,.2f}"


def describe_measure(measure: MeasureRef) -> str:
    """`count_if(is_on_time)` or `count(*)`."""
    return f"{measure.aggregation.value}({measure.attribute or '*'})"


def metric_definition(metric: Metric) -> dict[str, str]:
    """The governing definition of one metric, field by field."""
    formula = describe_measure(metric.numerator)
    if metric.denominator is not None:
        formula += f" / {describe_measure(metric.denominator)}"
    filters = [f"{f.attribute} {f.operator.value} {LIST_SEPARATOR.join(map(str, f.values))}" for f in metric.filters]
    return {
        "Definition": metric.description,
        "Grain": metric.grain,
        "Time attribution": metric.time_dimension,
        "Formula": formula,
        "Fixed filters": LIST_SEPARATOR.join(filters) or NONE_LISTED,
        "Owner": metric.owner.value,
        "Not to be confused with": LIST_SEPARATOR.join(metric.not_to_be_confused_with) or NONE_LISTED,
        "Defined in": metric.source,
    }


def display_frame(frame: pd.DataFrame, key_columns: tuple[str, ...], metrics: Mapping[str, Metric]) -> pd.DataFrame:
    """The result's key columns plus each metric column formatted for reading."""
    shown = frame[[c for c in key_columns if c in frame.columns]].copy()
    for metric_id, metric in metrics.items():
        shown[metric.label] = [format_value(v, metric.value_format) for v in frame[metric_id]]
    return shown


def clarification_followup(question: str, metric_id: str) -> str:
    """The question again with the chosen metric id appended, which binds it on the next ask."""
    return f"{question} ({metric_id})"


def catalog_table(catalog: SemanticCatalog) -> pd.DataFrame:
    """One row per metric for browsing: id, label, owner, grain, and the words that reach it."""
    rows = [{"Metric": m.id, "Label": m.label, "Owner": m.owner.value, "Grain": m.grain,
             "Time attribution": m.time_dimension, "Synonyms": LIST_SEPARATOR.join(m.synonyms),
             "Not to be confused with": LIST_SEPARATOR.join(m.not_to_be_confused_with)}
            for m in sorted(catalog.metrics.values(), key=lambda m: m.id)]
    return pd.DataFrame(rows)
