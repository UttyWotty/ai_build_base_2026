"""Streamlit-side access to the services: shared catalog, query service, and recipe comparison, and one NL service per session.

Tests and alternative setups inject their own objects through session state under the keys below.
Nothing here contacts the language model; the client only sends a request when a question is asked.
"""
from __future__ import annotations

import streamlit as st

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.services.demo_models import RecipeComparison
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.recipe_comparison import compare_recipes
from supply_ontology.services.service_factory import (
    default_llm_client,
    default_raw_database,
    load_default_catalog,
    load_team_recipes,
)

CATALOG_KEY = "catalog"
QUERY_SERVICE_KEY = "query_service"
LLM_CLIENT_KEY = "llm_client"
NL_SERVICE_KEY = "nl_service"
RECIPE_COMPARISON_KEY = "recipe_comparison"


@st.cache_resource
def _shared_catalog() -> SemanticCatalog:
    return load_default_catalog()


@st.cache_resource
def _shared_query_service() -> QueryService:
    return QueryService(_shared_catalog())


@st.cache_resource
def _shared_recipe_comparison() -> RecipeComparison:
    semantic = _shared_catalog()
    return compare_recipes(load_team_recipes(semantic), default_raw_database(), _shared_query_service())


def catalog() -> SemanticCatalog:
    """The injected catalog, else the shared one."""
    return st.session_state.get(CATALOG_KEY) or _shared_catalog()


def query_service() -> QueryService:
    """The injected query service, else the shared one over data/conformed."""
    return st.session_state.get(QUERY_SERVICE_KEY) or _shared_query_service()


def nl_service() -> NLService:
    """This session's NL service, built on first use."""
    if NL_SERVICE_KEY not in st.session_state:
        client = st.session_state.get(LLM_CLIENT_KEY) or default_llm_client()
        st.session_state[NL_SERVICE_KEY] = NLService(catalog(), query_service(), client)
    return st.session_state[NL_SERVICE_KEY]


def recipe_comparison() -> RecipeComparison:
    """The injected team recipe comparison, else the shared one over data/sources (computed once, no model)."""
    return st.session_state.get(RECIPE_COMPARISON_KEY) or _shared_recipe_comparison()
