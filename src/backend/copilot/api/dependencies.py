"""Request-scoped access to the long-lived services and the model selection, stored on the application state.

The services load once in the application lifespan; tests put their own bundle on the state instead.
Every data endpoint is async and runs on the event loop, so the shared DuckDB connections are used one call at a time.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Request

from copilot.services.agent_tools import CopilotTools
from copilot.services.factory import CopilotServices
from copilot.services.settings import DEMO_AS_OF
from llm_gateway.selection import ModelSelection

SERVICES_STATE = "services"
SELECTION_STATE = "selection"
SERVICE_UNAVAILABLE = 503
BAD_REQUEST = 400


def services(request: Request) -> CopilotServices:
    bundle = getattr(request.app.state, SERVICES_STATE, None)
    if bundle is None:
        raise HTTPException(SERVICE_UNAVAILABLE, "The copilot is still loading its data; try again in a few seconds.")
    return bundle


def selection(request: Request) -> ModelSelection:
    return getattr(request.app.state, SELECTION_STATE)


def parse_as_of(as_of: str | None) -> datetime:
    """The demo clock from an ISO timestamp, defaulting to the configured demo moment."""
    try:
        return datetime.fromisoformat(as_of or DEMO_AS_OF)
    except ValueError as error:
        raise HTTPException(BAD_REQUEST, f"as_of must be an ISO timestamp, got {as_of!r}") from error


def tools_at(request: Request, as_of: str | None) -> CopilotTools:
    return services(request).tools_at(parse_as_of(as_of))
