"""Browses the governed metric catalog: every metric with the words that reach it, and one metric's full definition.

This is the reference users check when an answer's definition surprises them.
The persona's own jargon is listed so each team sees how its words map onto shared metrics.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.ui.presenters import catalog_table, metric_definition


def render_catalog(catalog: SemanticCatalog, persona: str | None) -> None:
    """The metric table, the persona's jargon, and a definition picker."""
    st.dataframe(catalog_table(catalog), hide_index=True, width="stretch")
    if persona is not None:
        jargon = catalog.vocabulary.personas[persona].metric_vocabulary
        st.markdown(f"**{catalog.vocabulary.personas[persona].label} team phrases**")
        st.dataframe(pd.DataFrame(jargon.items(), columns=["Phrase", "Metric"]), hide_index=True)
    metric_id = st.selectbox("Definition of", sorted(catalog.metrics))
    definition = metric_definition(catalog.metrics[metric_id])
    st.table(pd.DataFrame(definition.items(), columns=["Field", "Value"]).set_index("Field"))
