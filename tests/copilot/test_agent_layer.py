"""Tests for the agent layer: tool result shaping, proposals, the answer check, evaluation scoring, and one offline
ADK run with a scripted model.

The ADK run uses a scripted BaseLlm and fake tools, so it exercises the real runner and tool calling without a network.
Proposals are written to a temporary file.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from pathlib import Path

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from copilot.core.agent_eval import EvalCase, ExpectedProposal, RunOutcome, score
from copilot.core.agent_views import ProposalError, build_proposal, impact_result
from copilot.core.answer_check import unexplained_numbers
from copilot.core.impact_analysis import assemble_report
from copilot.core.impact_model import AssetContext
from copilot.core.lead_history import LeadStats
from copilot.core.recovery_options import OptionInputs
from copilot.data_pipeline import adk_models
from copilot.data_pipeline.proposal_store import ProposalStore, ProposalStoreError
from copilot.services import agent_runner
from llm_gateway.selection import ModelSelection, Provider
from tests.copilot.fixtures import BEARING, ECONOMICS, T0, alert, bridge, position

ASSET = AssetContext("A-L1-01", "A", "A-L1", "PA")


def report():
    inputs = OptionInputs(alert(), T0, BEARING, position("A", 0), (position("B", 1),), bridge().transfer, None,
                          ECONOMICS, (), 2.0, None)
    return assemble_report(inputs, ASSET, LeadStats("spindle_bearing_wear", 0, None, None))


def test_impact_result_carries_quotable_numbers_and_the_recommendation() -> None:
    result = impact_result(report())
    recommended = [o for o in result["options"] if o["recommended_by_rules"]]
    assert len(recommended) == 1 and recommended[0]["kind"] == "transfer" and recommended[0]["total_cost_usd"] == 650.0
    assert result["spare"]["sister_sites"][0]["on_hand"] == 1 and "supplier" not in result


def test_proposals_take_numbers_from_the_report_and_reject_unknown_options(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.json")
    proposal = build_proposal(report(), "transfer", "B", " Replace the set. ", "", store.next_id("AL-2"), T0, "pending")
    record = store.add(proposal)
    assert record["extra_cost_usd"] == 650.0 and record["work_order_note"] == "Replace the set."
    assert store.set_status(record["proposal_id"], "approved")["status"] == "approved"
    assert store.next_id("AL-2") == "PR-AL-2-2"
    with pytest.raises(ProposalError, match="options are"):
        build_proposal(report(), "transfer", "Z", "", "", "x", T0, "pending")
    with pytest.raises(ProposalStoreError):
        store.set_status(record["proposal_id"], "done")


def test_answer_check_ignores_fingerprints_ids_and_thousands_separators() -> None:
    results = [{"cost": 4486.43, "share": 0.661}]
    assert unexplained_numbers("Cost $4,486.43, on time 66.1% (sql 59337a47eb2e9a5d, PR-AL-1-2026072502-1).", "", results) == []
    assert unexplained_numbers("It will cost 999 USD.", "", results) == ["999"]


def test_scoring_checks_tools_phrases_numbers_and_the_proposal() -> None:
    case = EvalCase("act", T0, "q", ("propose_action_plan",), ("approv",), ExpectedProposal("AL-2", "transfer", "B"))
    good = RunOutcome((("propose_action_plan", {"alert_id": "AL-2", "option_kind": "transfer", "option_source": "B"}),),
                      "Pending approval.", ())
    assert score(case, good) == []
    bad = RunOutcome((("list_open_alerts", {}),), "", ("7",))
    assert len(score(case, bad)) == 5


def test_local_selection_becomes_a_litellm_model_and_gemini_stays_a_name() -> None:
    assert adk_models.adk_model(ModelSelection(Provider.GEMINI, "gemini-x", "", 5.0)) == "gemini-x"
    local = adk_models.adk_model(ModelSelection(Provider.LOCAL, "qwen", "http://127.0.0.1:9/v1", 5.0))
    assert local.model == "openai/qwen"


class ScriptedLlm(BaseLlm):
    """Calls list_open_alerts first, then answers with a number taken from the tool result."""

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        answered = any(p.function_response for c in llm_request.contents for p in (c.parts or []))
        if not answered:
            part = types.Part(function_call=types.FunctionCall(name="list_open_alerts", args={}))
        else:
            part = types.Part(text="There are 2 open alerts.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


class FakeTools:
    """Duck-typed stand-in for CopilotTools with one real tool."""

    as_of = T0

    def safe(self, method):
        return method

    def list_open_alerts(self) -> dict:
        return {"count": 2, "alerts": ["AL-1", "AL-2"]}


def test_offline_adk_run_records_the_trace_and_verifies_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runner, "adk_model", lambda selection: ScriptedLlm(model="scripted"))
    run = agent_runner.run_copilot("How many alerts?", FakeTools(), ModelSelection(Provider.LOCAL, "scripted", "", 5.0))
    assert run.tools_used == ("list_open_alerts",) and run.answer == "There are 2 open alerts."
    assert run.verified and run.as_of == T0 and run.seconds < timedelta(minutes=1).total_seconds()


class TeamLlm(BaseLlm):
    """Specialists brief at once; the lead lists alerts, then answers."""

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        instruction = str(llm_request.config.system_instruction or "")
        answered = any(p.function_response for c in llm_request.contents for p in (c.parts or []))
        if "operations lead" not in instruction:
            role = instruction.split(".")[0].replace("You are the ", "")
            part = types.Part(text=f"{role} brief: 2 alerts.")
        elif not answered:
            part = types.Part(function_call=types.FunctionCall(name="list_open_alerts", args={}))
        else:
            part = types.Part(text="Lead: 2 alerts are open; plan follows.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def test_offline_team_run_separates_briefs_from_the_leads_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    from copilot.services import agent_team
    monkeypatch.setattr(agent_team, "adk_model", lambda selection: TeamLlm(model="scripted"))
    run = agent_runner.run_copilot("Triage the alerts", FakeTools(), ModelSelection(Provider.LOCAL, "scripted", "", 5.0),
                                   mode="team")
    briefs = {s.author for s in run.steps if s.kind == "brief"}
    assert briefs == {"maintenance_planner", "procurement_lead", "customer_lead"}
    assert run.answer == "Lead: 2 alerts are open; plan follows." and run.tools_used == ("list_open_alerts",)
    assert run.verified


class LoopingLlm(BaseLlm):
    """Never answers: calls a tool on every turn, like an agent guessing alert ids."""

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        part = types.Part(function_call=types.FunctionCall(name="list_open_alerts", args={}))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def test_a_looping_agent_is_stopped_by_the_call_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runner, "adk_model", lambda selection: LoopingLlm(model="scripted"))
    monkeypatch.setattr(agent_runner, "AGENT_MAX_LLM_CALLS_SINGLE", 3)
    run = agent_runner.run_copilot("Which alerts?", FakeTools(), ModelSelection(Provider.LOCAL, "scripted", "", 5.0))
    assert run.answer == "" and not run.verified and run.error_kind == "other"
    assert "3 model calls" in run.error_message and len(run.tools_used) <= 3


def test_every_team_member_can_list_the_open_alerts() -> None:
    from copilot.services.agent_team import ROLE_TOOLS
    assert all("list_open_alerts" in tools for tools in ROLE_TOOLS.values())
