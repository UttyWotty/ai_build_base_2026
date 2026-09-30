"""Streamlit-side access to the services: shared ones built once, per-session ones on first use, all overridable.

Tests inject their own objects through session state under the keys below, including file paths and a scripted model.
Nothing here contacts the language model; the investigation service only sends a request when a question is asked.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.services.command_center import (
    default_llm_client,
    load_default_catalog,
    replay_alerts,
)
from pdm_oee.services.investigation_service import InvestigationService
from pdm_oee.services.investigation_tools import ToolBox
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.settings import MODEL_DIR, OUTBOX_PATH, REPLAY_PATH

CATALOG_KEY, OEE_KEY, TOOLBOX_KEY = "catalog", "oee_service", "toolbox"
OUTBOX_KEY, REPLAY_KEY, MODEL_DIR_KEY = "outbox_path", "replay_path", "model_dir"
LLM_CLIENT_KEY, INVESTIGATION_KEY = "llm_client", "investigation"


@st.cache_resource
def _shared_catalog() -> PlantCatalog:
    return load_default_catalog()


@st.cache_resource
def _shared_oee() -> OEEService:
    return OEEService(_shared_catalog())


def catalog() -> PlantCatalog:
    return st.session_state.get(CATALOG_KEY) or _shared_catalog()


def oee() -> OEEService:
    return st.session_state.get(OEE_KEY) or _shared_oee()


def outbox_path() -> Path:
    return st.session_state.get(OUTBOX_KEY) or OUTBOX_PATH


def replay_path() -> Path:
    return st.session_state.get(REPLAY_KEY) or REPLAY_PATH


def model_dir() -> Path:
    return st.session_state.get(MODEL_DIR_KEY) or MODEL_DIR


def toolbox() -> ToolBox:
    if TOOLBOX_KEY not in st.session_state:
        st.session_state[TOOLBOX_KEY] = ToolBox(catalog(), oee(), replay_alerts(replay_path()))
    return st.session_state[TOOLBOX_KEY]


def investigation() -> InvestigationService:
    if INVESTIGATION_KEY not in st.session_state:
        client = st.session_state.get(LLM_CLIENT_KEY) or default_llm_client()
        st.session_state[INVESTIGATION_KEY] = InvestigationService(toolbox(), client)
    return st.session_state[INVESTIGATION_KEY]


def mode_labels() -> dict[str, str]:
    return {m.id: m.label for c in catalog().plant.asset_classes.values() for m in c.failure_modes.values()}
