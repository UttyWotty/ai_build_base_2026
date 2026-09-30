"""Answers investigation questions with the local model driving governed tools, and checks the answer's numbers.

Each model reply is one tool call or a final answer. Invalid calls and tool errors go back to the model as problems;
a final answer whose numbers no tool returned gets one retry, and is marked unverified if it still has such numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from pdm_oee.core.investigation_protocol import (
    FinalAnswer,
    ReplyError,
    ToolCall,
    parse_reply,
    problem_message,
    system_message,
    tool_result_message,
    user_message,
)
from pdm_oee.core.number_check import unverified_numbers
from pdm_oee.core.tool_catalog import validate_call
from pdm_oee.data_pipeline.llm_client import LLMClient, LLMError, build_llm_client
from pdm_oee.services.investigation_tools import ToolBox, ToolError

MAX_TOOL_CALLS = 6
EXTRA_TURNS = 3
ANSWER_NOW = "You have used all tool calls. Reply now with a final answer from the results you have."
MODEL_UNAVAILABLE, TURNS_EXHAUSTED, ANSWERED = "model_unavailable", "turns_exhausted", "answered"


@dataclass(frozen=True)
class Step:
    tool: str
    arguments: dict
    result: object


@dataclass(frozen=True)
class Investigation:
    question: str
    answer: str | None
    verified: bool
    unverified: tuple[str, ...]
    steps: tuple[Step, ...]
    status: str
    problems: tuple[str, ...] = field(default=())

    @property
    def tools_used(self) -> tuple[str, ...]:
        return tuple(step.tool for step in self.steps)


class InvestigationService:
    """Question in, tool-backed answer out."""

    def __init__(self, toolbox: ToolBox, llm_client: LLMClient | None = None, max_tool_calls: int = MAX_TOOL_CALLS) -> None:
        self.toolbox = toolbox
        self.llm_client = llm_client or build_llm_client()
        self.max_tool_calls = max_tool_calls
        dates = pd.to_datetime(toolbox.oee.measures["shift_date"])
        self.system = system_message(toolbox.vocabularies(), dates.min().date(), dates.max().date())

    def ask(self, question: str) -> Investigation:
        messages, steps, problems, retried = [self.system, user_message(question)], [], [], False
        for _ in range(self.max_tool_calls + EXTRA_TURNS):
            try:
                reply = self.llm_client.complete(messages)
            except LLMError as error:
                return Investigation(question, None, False, (), tuple(steps), MODEL_UNAVAILABLE, (str(error),))
            messages.append({"role": "assistant", "content": reply})
            try:
                decision = parse_reply(reply)
            except ReplyError as error:
                problems.append(str(error))
                messages.append(problem_message([str(error)]))
                continue
            if isinstance(decision, FinalAnswer):
                missing = unverified_numbers(decision.text, question, [s.result for s in steps])
                if missing and not retried:
                    retried = True
                    messages.append(problem_message([f"These numbers were not returned by any tool: {', '.join(missing)}. "
                                                     "Quote tool results exactly or leave the numbers out."]))
                    continue
                return Investigation(question, decision.text, not missing, tuple(missing), tuple(steps), ANSWERED, tuple(problems))
            messages.append(self._run(decision, steps, problems))
        return Investigation(question, None, False, (), tuple(steps), TURNS_EXHAUSTED, tuple(problems))

    def _run(self, call: ToolCall, steps: list[Step], problems: list[str]) -> dict[str, str]:
        if len(steps) >= self.max_tool_calls:
            return {"role": "user", "content": ANSWER_NOW}
        arguments, issues = validate_call(call.tool, call.arguments, self.toolbox.vocabularies())
        if issues:
            problems.extend(issues)
            return problem_message(issues)
        try:
            result = self.toolbox.run(call.tool, arguments)
        except ToolError as error:
            problems.append(str(error))
            return problem_message([str(error)])
        steps.append(Step(call.tool, {k: str(v) for k, v in arguments.items()}, result))
        return tool_result_message(call.tool, result)

