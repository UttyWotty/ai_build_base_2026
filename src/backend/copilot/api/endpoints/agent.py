"""The agent endpoint: ask the copilot a question and stream its work as server-sent events.

Each tool call, tool result, and text arrives as it happens; the last event carries the answer, whether its numbers
were verified, and any provider error. The browser shows the agent working instead of a spinner.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from copilot.api.dependencies import selection, tools_at
from copilot.services.agent_runner import (
    SINGLE,
    TEAM,
    AgentRun,
    AgentStep,
    stream_copilot,
)

router = APIRouter(prefix="/api/agent")
EVENT_STREAM = "text/event-stream"
MODES = frozenset({SINGLE, TEAM})
BAD_REQUEST = 400
NO_BUFFERING = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class Question(BaseModel):
    """A question at a demo clock."""

    question: str
    as_of: str | None = None
    # "single" for one agent, "team" for the specialists and the lead.
    mode: str = SINGLE


@router.post("/stream")
async def stream(body: Question, request: Request) -> StreamingResponse:
    tools = tools_at(request, body.as_of)
    if body.mode not in MODES:
        raise HTTPException(BAD_REQUEST, f"mode must be one of {', '.join(sorted(MODES))}")
    events = _events(stream_copilot(body.question, tools, selection(request), body.mode))
    return StreamingResponse(events, media_type=EVENT_STREAM, headers=NO_BUFFERING)


async def _events(source: AsyncIterator[AgentStep | AgentRun]) -> AsyncIterator[str]:
    async for item in source:
        yield _sse(_step_event(item) if isinstance(item, AgentStep) else _done_event(item))


def _step_event(step: AgentStep) -> dict[str, object]:
    return {"type": step.kind, "name": step.name, "payload": step.payload, "author": step.author}


def _done_event(run: AgentRun) -> dict[str, object]:
    return {"type": "done", "answer": run.answer, "verified": run.verified, "error": run.error,
            "unexplained_numbers": list(run.unexplained_numbers), "seconds": run.seconds, "model": run.model,
            "tools_used": list(run.tools_used)}


def _sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(jsonable_encoder(event))}\n\n"
