"""Builds the copilot's services from the configured locations, so entry points never wire adapters themselves.

One world store is shared by every service built from the same factory call.
Tests build services directly with in-memory stores instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from copilot.data_pipeline.bridge_files import load_bridge
from copilot.data_pipeline.impact_queries import site_assets
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.data_pipeline.record_store import RecordStore
from copilot.data_pipeline.world_store import WorldStore
from copilot.services.agent_tools import CopilotTools
from copilot.services.alert_book import AlertBook
from copilot.services.decisions import DecisionBook, OutcomeService
from copilot.services.field_service import FieldInputService
from copilot.services.impact_service import ImpactService
from copilot.services.settings import (
    BRIDGE_DATA_DIR,
    BRIDGE_SEMANTIC_DIR,
    INSPECTIONS_PATH,
    PLANT_CONFORMED_DIR,
    PLANT_SEMANTIC_DIR,
    PROPOSALS_PATH,
    SUPPLIER_UPDATES_PATH,
    SUPPLY_CONFORMED_DIR,
)
from copilot.services.supplier_reliability import SupplierReliabilityService
from copilot.services.value_service import ValueService
from llm_gateway.factory import default_selection
from llm_gateway.multimodal import build_reader
from pdm_oee.core.catalog import PlantCatalog
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
    """The impact service over the configured data, without approvals applied (the pure analysis)."""
    store = connection_manager or default_world_store()
    reliability = SupplierReliabilityService(QueryService(load_supply_catalog()), store)
    return ImpactService(load_bridge(BRIDGE_SEMANTIC_DIR), load_catalog(PLANT_SEMANTIC_DIR),
                         alerts or default_alert_book(), reliability, store)


@dataclass(frozen=True)
class CopilotServices:
    """The long-lived services; tools for a given analysis time are cheap to build from them."""

    impact: ImpactService
    plant_tools: ToolBox
    plant_catalog: PlantCatalog
    reliability: SupplierReliabilityService
    proposals: ProposalStore
    value: ValueService
    outcomes: OutcomeService
    field: FieldInputService

    def tools_at(self, as_of: datetime) -> CopilotTools:
        return CopilotTools(as_of, self.impact, self.plant_tools, self.plant_catalog, self.reliability, self.proposals,
                            self.field)


def default_services(proposals_path: Path = PROPOSALS_PATH, field_dir: Path | None = None) -> CopilotServices:
    """Every copilot service over the configured data; tests pass their own proposals file and field-input folder."""
    store = default_world_store()
    alerts = default_alert_book()
    reliability = SupplierReliabilityService(QueryService(load_supply_catalog()), store)
    plant_catalog = load_catalog(PLANT_SEMANTIC_DIR)
    bridge = load_bridge(BRIDGE_SEMANTIC_DIR)
    proposals = ProposalStore(proposals_path)
    book = DecisionBook(proposals, alerts, bridge, site_assets(store))
    field = FieldInputService(build_reader(default_selection()), alerts, plant_catalog,
                              RecordStore(field_dir / "inspections.json" if field_dir else INSPECTIONS_PATH),
                              RecordStore(field_dir / "supplier_updates.json" if field_dir else SUPPLIER_UPDATES_PATH))
    impact = ImpactService(bridge, plant_catalog, alerts, reliability, store, decisions=book.decisions,
                           supplier_updates=field.supplier_updates)
    # The track record scores the pure analysis, so demo approvals never change it.
    pure = ImpactService(bridge, plant_catalog, alerts, reliability, store)
    plant_tools = ToolBox(plant_catalog, OEEService(plant_catalog), read_replay_alerts(REPLAY_PATH))
    return CopilotServices(impact, plant_tools, plant_catalog, reliability, proposals, ValueService(pure),
                           OutcomeService(book, pure.analyse, pure.pf_days), field)


def default_copilot_tools(as_of: datetime) -> CopilotTools:
    """The agent's tools over the configured data, at one analysis time."""
    return default_services().tools_at(as_of)
