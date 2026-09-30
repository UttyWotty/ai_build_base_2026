"""Runs the operations copilot on the Agent Development Kit and records what it did.

Each run builds an LlmAgent with the governed tools for one analysis time and sends one message. stream_copilot yields
every tool call, tool result, and text as it happens, then the finished run, whose answer is checked number by number.
"""
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from copilot.core.agent_instructions import copilot_instruction
from copilot.core.answer_check import unexplained_numbers
from copilot.core.errors import CopilotError
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
    return asyncio.run(_last(stream_copilot(question, tools, selection)))


async def stream_copilot(question: str, tools: CopilotTools,
                         selection: ModelSelection) -> AsyncIterator[AgentStep | AgentRun]:
    """Yield each step as the agent takes it, then the finished, checked run."""
    started = time.monotonic()
    steps: list[AgentStep] = []
    try:
        async for step in _steps(build_agent(tools, selection), question):
            steps.append(step)
            yield step
    except Exception as error:  # the model provider can fail in many ways; the run records it instead of crashing
        failed = AgentStep("error", type(error).__name__, _short(error))
        yield failed
        yield AgentRun(question, tools.as_of, selection.label, tuple(steps) + (failed,), "", (),
                       round(time.monotonic() - started, 1), error=_short(error))
        return
    yield finish_run(question, tools, selection, steps, started)


def finish_run(question: str, tools: CopilotTools, selection: ModelSelection, steps: list[AgentStep],
               started: float) -> AgentRun:
    """Assemble the answer from the text steps and check its numbers against the tool results."""
    answer = "\n".join(str(s.payload) for s in steps if s.kind == "text").strip()
    results = tuple(s.payload for s in steps if s.kind == "tool_result")
    return AgentRun(question, tools.as_of, selection.label, tuple(steps), answer,
                    tuple(unexplained_numbers(answer, question, results)), round(time.monotonic() - started, 1), results)


async def _last(stream: AsyncIterator[AgentStep | AgentRun]) -> AgentRun:
    final = None
    async for item in stream:
        final = item
    if not isinstance(final, AgentRun):
        raise CopilotError("The agent stream ended without a finished run")
    return final


def _short(error: Exception) -> str:
    """The provider's status line (for example "429 RESOURCE_EXHAUSTED ...") or, failing that, the first line."""
    text = str(error).strip()
    status = STATUS_PATTERN.search(text)
    if status:
        return text[status.start():status.start() + ERROR_CHARS]
    return (text.splitlines()[0] if text else type(error).__name__)[:ERROR_CHARS]


async def _steps(agent: LlmAgent, question: str) -> AsyncIterator[AgentStep]:
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role=USER_ROLE, parts=[types.Part(text=question)])
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
        for call in event.get_function_calls():
            yield AgentStep("tool_call", call.name or "", dict(call.args or {}))
        for response in event.get_function_responses():
            yield AgentStep("tool_result", response.name or "", response.response)
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and not part.thought:
                    yield AgentStep("text", AGENT_NAME, part.text)
