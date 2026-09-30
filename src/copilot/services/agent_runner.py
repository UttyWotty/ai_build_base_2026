"""Runs the operations copilot on the Agent Development Kit and records what it did.

Each run builds an LlmAgent with the governed tools for one analysis time, sends one message, and collects the trace:
tool calls, tool results, and the final answer, which is then checked number by number against the tool results.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from copilot.core.agent_instructions import copilot_instruction
from copilot.core.answer_check import unexplained_numbers
from copilot.data_pipeline.adk_models import adk_model
from copilot.services.agent_functions import adk_functions
from copilot.services.agent_tools import CopilotTools
from llm_gateway.selection import ModelSelection

APP_NAME = "operations_copilot"
AGENT_NAME = "operations_copilot"
USER_ID = "operator"
USER_ROLE = "user"
TEMPERATURE = 0.0
ERROR_CHARS = 300
STATUS_PATTERN = re.compile(r"\b[45]\d\d [A-Z_]{4,}")
# Free-tier and shared quotas answer 429 under bursts; the SDK retries these with backoff before the run fails.
RETRY_OPTIONS = types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0,
                                       http_status_codes=[429, 500, 502, 503, 504])


@dataclass(frozen=True)
class AgentStep:
    """One step of the trace: a tool call, a tool result, or text from the agent."""

    kind: str
    name: str
    payload: object


@dataclass(frozen=True)
class AgentRun:
    """A finished run."""

    question: str
    as_of: datetime
    model: str
    steps: tuple[AgentStep, ...]
    answer: str
    unexplained_numbers: tuple[str, ...]
    seconds: float
    tool_results: tuple[object, ...] = field(default=())
    # Why the run failed before answering, for example a quota limit; empty when it answered.
    error: str = ""

    @property
    def verified(self) -> bool:
        return bool(self.answer) and not self.unexplained_numbers

    @property
    def tools_used(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.steps if s.kind == "tool_call")


def build_agent(tools: CopilotTools, selection: ModelSelection) -> LlmAgent:
    """The copilot agent for one analysis time."""
    return LlmAgent(name=AGENT_NAME, model=adk_model(selection), instruction=copilot_instruction(tools.as_of),
                    tools=adk_functions(tools),
                    generate_content_config=types.GenerateContentConfig(
                        temperature=TEMPERATURE, http_options=types.HttpOptions(retry_options=RETRY_OPTIONS)))


def run_copilot(question: str, tools: CopilotTools, selection: ModelSelection) -> AgentRun:
    """Ask the copilot one question and return the checked trace."""
    started = time.monotonic()
    try:
        steps = asyncio.run(_run(build_agent(tools, selection), question))
    except Exception as error:  # the model provider can fail in many ways; the run records it instead of crashing
        return AgentRun(question, tools.as_of, selection.label, (AgentStep("error", type(error).__name__, str(error)),),
                        "", (), round(time.monotonic() - started, 1), error=_short(error))
    answer = "\n".join(str(s.payload) for s in steps if s.kind == "text").strip()
    results = tuple(s.payload for s in steps if s.kind == "tool_result")
    return AgentRun(question, tools.as_of, selection.label, tuple(steps), answer,
                    tuple(unexplained_numbers(answer, question, results)), round(time.monotonic() - started, 1), results)


def _short(error: Exception) -> str:
    """The provider's status line (for example "429 RESOURCE_EXHAUSTED ...") or, failing that, the first line."""
    text = str(error).strip()
    status = STATUS_PATTERN.search(text)
    if status:
        return text[status.start():status.start() + ERROR_CHARS]
    return (text.splitlines()[0] if text else type(error).__name__)[:ERROR_CHARS]


async def _run(agent: LlmAgent, question: str) -> list[AgentStep]:
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role=USER_ROLE, parts=[types.Part(text=question)])
    steps: list[AgentStep] = []
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
        steps += [AgentStep("tool_call", c.name or "", dict(c.args or {})) for c in event.get_function_calls()]
        steps += [AgentStep("tool_result", r.name or "", r.response) for r in event.get_function_responses()]
        if event.is_final_response() and event.content and event.content.parts:
            steps += [AgentStep("text", AGENT_NAME, p.text) for p in event.content.parts if p.text and not p.thought]
    return steps
