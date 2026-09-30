"""Builds the copilot's services from the configured locations, so entry points never wire adapters themselves.

One world store is shared by every service built from the same factory call.
Tests build services directly with in-memory stores instead.
"""
from __future__ import annotations

from datetime import datetime

from copilot.data_pipeline.bridge_files import load_bridge
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.data_pipeline.world_store import WorldStore
from copilot.services.agent_tools import CopilotTools
from copilot.services.alert_book import AlertBook
from copilot.services.impact_service import ImpactService
from copilot.services.settings import (
    BRIDGE_DATA_DIR,
    BRIDGE_SEMANTIC_DIR,
    PLANT_CONFORMED_DIR,
    PLANT_SEMANTIC_DIR,
    PROPOSALS_PATH,
    SUPPLY_CONFORMED_DIR,
)
from copilot.services.supplier_reliability import SupplierReliabilityService
from pdm_oee.data_pipeline.replay_store import read_replay_alerts
from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.services.investigation_tools import ToolBox
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.settings import REPLAY_PATH
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.service_factory import (
    load_default_catalog as load_supply_catalog,
)


def default_world_store() -> WorldStore:
    """Views over both worlds and the bridge data."""
    return WorldStore(PLANT_CONFORMED_DIR, SUPPLY_CONFORMED_DIR, BRIDGE_DATA_DIR)


def default_alert_book() -> AlertBook:
    return AlertBook(read_replay_alerts(REPLAY_PATH))


def default_impact_service(connection_manager: WorldStore | None = None, alerts: AlertBook | None = None) -> ImpactService:
    """The impact service over the configured data."""
    store = connection_manager or default_world_store()
    reliability = SupplierReliabilityService(QueryService(load_supply_catalog()), store)
    return ImpactService(load_bridge(BRIDGE_SEMANTIC_DIR), load_catalog(PLANT_SEMANTIC_DIR),
                         alerts or default_alert_book(), reliability, store)


def default_copilot_tools(as_of: datetime) -> CopilotTools:
    """The agent's tools over the configured data, at one analysis time."""
    store = default_world_store()
    alerts = default_alert_book()
    reliability = SupplierReliabilityService(QueryService(load_supply_catalog()), store)
    plant_catalog = load_catalog(PLANT_SEMANTIC_DIR)
    impact = ImpactService(load_bridge(BRIDGE_SEMANTIC_DIR), plant_catalog, alerts, reliability, store)
    plant_tools = ToolBox(plant_catalog, OEEService(plant_catalog), read_replay_alerts(REPLAY_PATH))
    return CopilotTools(as_of, impact, plant_tools, plant_catalog, reliability, ProposalStore(PROPOSALS_PATH))
