"""Renders one natural-language response: the governed answer with its definition and SQL, a clarification, or a refusal.

Clarification options are buttons that queue a follow-up question binding the chosen metric.
Every answer states how its metric was resolved and the data's as-of date.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.sql_fragments import PERIOD_COLUMN
from supply_ontology.services.nl_models import (
    RESOLVED_BY_WORDING,
    Answer,
    Clarification,
    NLResponse,
)
from supply_ontology.ui.presenters import (
    clarification_followup,
    display_frame,
    format_value,
    metric_definition,
)

PENDING_QUESTION_KEY = "pending_question"


def render_response(response: NLResponse, catalog: SemanticCatalog) -> None:
    """Show whichever outcome the service produced."""
    if isinstance(response, Answer):
        render_answer(response)
    elif isinstance(response, Clarification):
        render_clarification(response, catalog)
    else:
        st.warning(f"Not answered: {response.reason}")


def render_answer(answer: Answer) -> None:
    result = answer.result
    metrics = {m.id: m for m in result.metrics}
    frame = display_frame(result.frame, result.compiled.key_columns, metrics)
    if len(result.frame) == 1 and not result.compiled.key_columns and len(metrics) == 1:
        metric = result.metrics[0]
        st.metric(metric.label, format_value(result.frame[metric.id].iloc[0], metric.value_format))
    else:
        st.dataframe(frame, hide_index=True, width="stretch")
        _render_trend(result.frame, result.compiled.key_columns, tuple(metrics))
    how = (f"the wording ({', '.join(answer.matched_terms)})" if answer.resolved_by == RESOLVED_BY_WORDING
           else "the model, from the catalog")
    period = result.spec.time_range
    span = "all data" if period is None else f"{period.start} to {period.end}"
    st.caption(f"Metric chosen by {how}. Period: {span}. Data as of {result.as_of}.")
    for metric in result.metrics:
        with st.expander(f"Definition: {metric.label} ({metric.id})"):
            st.table(pd.DataFrame(metric_definition(metric).items(), columns=["Field", "Value"]).set_index("Field"))
    with st.expander(f"SQL (fingerprint {result.compiled.fingerprint})"):
        st.code(result.compiled.sql, language="sql")
        st.caption(f"Bound parameters: {list(result.compiled.parameters)}")


def render_clarification(clarification: Clarification, catalog: SemanticCatalog) -> None:
    st.info(clarification.prompt)
    for option in clarification.options:
        metric = catalog.metric(option)
        label = option if metric is None else f"{metric.label} ({option})"
        if st.button(label, key=f"clarify-{option}"):
            st.session_state[PENDING_QUESTION_KEY] = clarification_followup(clarification.question, option)
            st.rerun()


def _render_trend(frame: pd.DataFrame, key_columns: tuple[str, ...], metric_ids: tuple[str, ...]) -> None:
    """A line chart when the result is a single-metric trend with at most one grouping."""
    groups = [c for c in key_columns if c != PERIOD_COLUMN]
    if PERIOD_COLUMN not in key_columns or len(metric_ids) != 1 or len(groups) > 1:
        return
    chart = frame.pivot_table(index=PERIOD_COLUMN, columns=groups or None, values=metric_ids[0]) if groups \
        else frame.set_index(PERIOD_COLUMN)[[metric_ids[0]]]
    st.line_chart(chart)
