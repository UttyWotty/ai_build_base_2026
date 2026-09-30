"""The operations team on the Agent Development Kit: specialists in parallel, then a lead who decides and proposes.

A SequentialAgent runs a ParallelAgent of three specialists (maintenance, procurement, customer), each with only the
tools of its role and an output key that stores its brief in session state, and then the lead, whose instruction reads
those briefs. All events stream through one runner, so the whole team's work appears in the trace.
"""
from __future__ import annotations

from collections.abc import Callable

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.genai import types

from copilot.core.team_instructions import (
    CUSTOMER_BRIEF,
    MAINTENANCE_BRIEF,
    PROCUREMENT_BRIEF,
    customer_instruction,
    lead_instruction,
    maintenance_instruction,
    procurement_instruction,
)
from copilot.data_pipeline.adk_models import adk_model
from copilot.services.agent_functions import adk_functions
from copilot.services.agent_tools import CopilotTools
from llm_gateway.selection import ModelSelection

TEAM_NAME = "operations_team"
SPECIALISTS_NAME = "specialists"
LEAD_NAME = "operations_lead"
ROLE_TOOLS = {
    "maintenance_planner": ("get_sensor_evidence", "get_field_reports", "work_order_history", "failures"),
    "procurement_lead": ("analyse_alert_impact", "get_supplier_record"),
    "customer_lead": ("analyse_alert_impact",),
    LEAD_NAME: ("list_open_alerts", "analyse_alert_impact", "propose_action_plan"),
}


def build_team(tools: CopilotTools, selection: ModelSelection, config: types.GenerateContentConfig) -> SequentialAgent:
    """The team for one analysis time."""
    functions = {f.__name__: f for f in adk_functions(tools)}

    def member(name: str, instruction: str, output_key: str | None = None) -> LlmAgent:
        return LlmAgent(name=name, model=adk_model(selection), instruction=instruction, output_key=output_key,
                        tools=[functions[t] for t in ROLE_TOOLS[name]], generate_content_config=config)

    specialists = ParallelAgent(name=SPECIALISTS_NAME, sub_agents=[
        member("maintenance_planner", maintenance_instruction(tools.as_of), MAINTENANCE_BRIEF),
        member("procurement_lead", procurement_instruction(tools.as_of), PROCUREMENT_BRIEF),
        member("customer_lead", customer_instruction(tools.as_of), CUSTOMER_BRIEF),
    ])
    return SequentialAgent(name=TEAM_NAME, sub_agents=[specialists, member(LEAD_NAME, lead_instruction(tools.as_of))])


def answering_agents() -> frozenset[str]:
    """Agents whose final text is the answer; every other agent's text is a brief."""
    return frozenset({LEAD_NAME})


TeamBuilder = Callable[[CopilotTools, ModelSelection, types.GenerateContentConfig], SequentialAgent]
