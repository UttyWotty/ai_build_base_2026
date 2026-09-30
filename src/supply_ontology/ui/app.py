"""Streamlit entry point: ask governed questions as a team, replay the consistency demo, and browse the metric catalog.

Run with `make ui`. The page loads the catalog and data but contacts the local model only when a question is asked.
Example questions and clarification choices queue a question in session state and rerun the page to answer it.
"""
from __future__ import annotations

import streamlit as st

from supply_ontology.services.service_factory import load_saved_demo_runs
from supply_ontology.services.settings import LLM_BASE_URL, LLM_MODEL
from supply_ontology.ui.answer_view import PENDING_QUESTION_KEY, render_response
from supply_ontology.ui.catalog_view import render_catalog
from supply_ontology.ui.demo_view import render_recipe_comparison, render_saved_demo
from supply_ontology.ui.resources import catalog, nl_service, recipe_comparison

PAGE_TITLE = "Governed Supply Chain Metrics"
RESPONSE_KEY = "last_response"
NO_PERSONA_LABEL = "No team"
TAB_NAMES = ("Ask", "Consistency demo", "Metric catalog")


def main() -> None:
    """Lay out the sidebar and the three tabs."""
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)
    semantic = catalog()
    personas = semantic.vocabulary.personas
    with st.sidebar:
        persona = st.selectbox("Team", [None, *personas],
                               format_func=lambda p: NO_PERSONA_LABEL if p is None else personas[p].label)
        st.caption(f"Model: {LLM_MODEL} at {LLM_BASE_URL}")
    ask_tab, demo_tab, catalog_tab = st.tabs(TAB_NAMES)
    with ask_tab:
        render_ask(persona)
    with demo_tab:
        render_recipe_comparison(recipe_comparison())
        st.divider()
        render_saved_demo(load_saved_demo_runs())
    with catalog_tab:
        render_catalog(semantic, persona)


def render_ask(persona: str | None) -> None:
    """Question box, example questions for the team, and the latest response."""
    semantic = catalog()
    if persona is not None:
        for example in semantic.vocabulary.personas[persona].example_questions:
            if st.button(example, key=f"example-{example}"):
                st.session_state[PENDING_QUESTION_KEY] = example
                st.rerun()
    question = st.session_state.pop(PENDING_QUESTION_KEY, None)
    with st.form("ask"):
        typed = st.text_input("Question", placeholder="What was our service level last quarter?")
        if st.form_submit_button("Ask") and typed.strip():
            question = typed.strip()
    if question:
        with st.spinner("Resolving against the governed catalog"):
            st.session_state[RESPONSE_KEY] = nl_service().ask(question, persona)
    if RESPONSE_KEY in st.session_state:
        response = st.session_state[RESPONSE_KEY]
        st.markdown(f"**{response.question}**")
        render_response(response, semantic)


main()
