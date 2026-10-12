"""Runs the operations copilot on the Agent Development Kit and records what it did.

Each run builds an LlmAgent with the governed tools for one analysis time and sends one message. stream_copilot yields
every tool call, tool result, and text as it happens, then the finished run, whose answer is checked number by number.
"""
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from datetime import datetime

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from copilot.core.agent_instructions import copilot_instruction
from copilot.core.answer_check import unexplained_numbers
from copilot.core.errors import CopilotError
from copilot.core.provider_errors import classify
from copilot.data_pipeline.adk_models import adk_model
from copilot.services.agent_functions import adk_functions
from copilot.services.agent_team import answering_agents, build_team
from copilot.services.agent_tools import CopilotTools
from copilot.services.settings import (
    AGENT_MAX_LLM_CALLS_SINGLE,
    AGENT_MAX_LLM_CALLS_TEAM,
)
from llm_gateway.selection import ModelSelection, Provider
from llm_gateway.settings import GEMINI_FALLBACK_MODELS

APP_NAME = "operations_copilot"
SINGLE = "single"
TEAM = "team"
AGENT_NAME = "operations_copilot"
USER_ID = "operator"
USER_ROLE = "user"
TEMPERATURE = 0.0
ERROR_CHARS = 300
STATUS_PATTERN = re.compile(r"\b[45]\d\d [A-Z_]{4,}")
# Free-tier and shared quotas answer 429 under bursts; the SDK retries these with backoff before the run fails.
OTHER_KIND = "other"
CALL_CAP_MESSAGE = ("The agents used their {cap} model calls for one run without finishing, so the run was stopped to "
                    "protect the demo's budget. Ask about a specific alert, or try again.")
RETRY_OPTIONS = types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0,
                                       http_status_codes=[429, 500, 502, 503, 504])


@dataclass(frozen=True)
class AgentStep:
    """One step of the trace: a tool call, a tool result, a specialist's brief, or the answer's text."""

    kind: str
    name: str
    payload: object
    # The agent that took the step; in team mode it tells the specialists and the lead apart.
    author: str = ""


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
    # The plain-language issue behind the error, and its kind (quota, overloaded, auth, model_unavailable, other).
    error_message: str = ""
    error_kind: str = ""

    @property
    def verified(self) -> bool:
        return bool(self.answer) and not self.unexplained_numbers

    @property
    def tools_used(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.steps if s.kind == "tool_call")


def _config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(temperature=TEMPERATURE,
                                       http_options=types.HttpOptions(retry_options=RETRY_OPTIONS))


def build_agent(tools: CopilotTools, selection: ModelSelection, mode: str = SINGLE) -> BaseAgent:
    """The single copilot agent, or the operations team, for one analysis time."""
    if mode == TEAM:
        return build_team(tools, selection, _config())
    if mode != SINGLE:
        raise CopilotError(f"Unknown agent mode {mode!r}; expected {SINGLE} or {TEAM}")
    return LlmAgent(name=AGENT_NAME, model=adk_model(selection), instruction=copilot_instruction(tools.as_of),
                    tools=adk_functions(tools), generate_content_config=_config())


def run_copilot(question: str, tools: CopilotTools, selection: ModelSelection, mode: str = SINGLE) -> AgentRun:
    """Ask the copilot one question and return the checked trace."""
    return asyncio.run(_last(stream_copilot(question, tools, selection, mode)))


async def stream_copilot(question: str, tools: CopilotTools, selection: ModelSelection,
                         mode: str = SINGLE) -> AsyncIterator[AgentStep | AgentRun]:
    """Yield each step as the agent (or the team) takes it, then the finished, checked run.

    When a Gemini model is out of quota or unavailable, the run restarts on the next backup model and says so.
    """
    started = time.monotonic()
    answerers = answering_agents() if mode == TEAM else frozenset({AGENT_NAME})
    candidates = _candidates(selection)
    for index, current in enumerate(candidates):
        steps: list[AgentStep] = []
        try:
            async for step in _steps(build_agent(tools, current, mode), question, answerers, _call_cap(mode)):
                steps.append(step)
                yield step
        except LlmCallsLimitExceededError as error:
            stopped = AgentStep("error", type(error).__name__, _short(error))
            yield stopped
            yield AgentRun(question, tools.as_of, current.label, tuple(steps) + (stopped,), "", (),
                           round(time.monotonic() - started, 1), error=_short(error),
                           error_message=CALL_CAP_MESSAGE.format(cap=_call_cap(mode)), error_kind=OTHER_KIND)
            return
        except Exception as error:  # the model provider can fail in many ways; the run records it instead of crashing
            issue = classify(_short(error), current.label)
            if issue.try_another_model and index + 1 < len(candidates):
                yield AgentStep("notice", "fallback", f"{issue.message} Switching to {candidates[index + 1].label}.")
                continue
            failed = AgentStep("error", type(error).__name__, _short(error))
            yield failed
            yield AgentRun(question, tools.as_of, current.label, tuple(steps) + (failed,), "", (),
                           round(time.monotonic() - started, 1), error=_short(error), error_message=issue.message,
                           error_kind=issue.kind.value)
            return
        yield finish_run(question, tools, current, steps, started)
        return


def _candidates(selection: ModelSelection) -> list[ModelSelection]:
    """The selected model, then the configured Gemini backups."""
    if selection.provider is not Provider.GEMINI:
        return [selection]
    backups = [m for m in GEMINI_FALLBACK_MODELS if m != selection.model]
    return [selection] + [replace(selection, model=m) for m in backups]


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


def _call_cap(mode: str) -> int:
    return AGENT_MAX_LLM_CALLS_TEAM if mode == TEAM else AGENT_MAX_LLM_CALLS_SINGLE


async def _steps(agent: BaseAgent, question: str, answerers: frozenset[str], cap: int) -> AsyncIterator[AgentStep]:
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role=USER_ROLE, parts=[types.Part(text=question)])
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message,
                                        run_config=RunConfig(max_llm_calls=cap)):
        author = event.author or ""
        for call in event.get_function_calls():
            yield AgentStep("tool_call", call.name or "", dict(call.args or {}), author)
        for response in event.get_function_responses():
            yield AgentStep("tool_result", response.name or "", response.response, author)
        if event.is_final_response() and event.content and event.content.parts:
            kind = "text" if author in answerers else "brief"
            for part in event.content.parts:
                if part.text and not part.thought:
                    yield AgentStep(kind, author, part.text, author)
