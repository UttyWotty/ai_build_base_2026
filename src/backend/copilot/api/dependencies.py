"""Request-scoped access to the long-lived services and the model selection, stored on the application state.

The services load once in the application lifespan; tests put their own bundle on the state instead.
Every data endpoint is async and runs on the event loop, so the shared DuckDB connections are used one call at a time.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from copilot.core.usage_limit import (
    LimitDecision,
    UsageLimiter,
    UsageLimits,
    limit_message,
)
from copilot.services.agent_tools import CopilotTools
from copilot.services.factory import CopilotServices
from copilot.services.settings import (
    DEMO_AS_OF,
    USAGE_LIMIT_PER_VISITOR,
    USAGE_LIMIT_TOTAL,
    USAGE_LIMIT_WINDOW_MINUTES,
)
from llm_gateway.selection import ModelSelection

SERVICES_STATE = "services"
SELECTION_STATE = "selection"
LIMITER_STATE = "limiter"
TOO_MANY_REQUESTS = 429
FORWARDED_FOR = "x-forwarded-for"
RETRY_AFTER = "Retry-After"
UNKNOWN_VISITOR = "unknown"
SERVICE_UNAVAILABLE = 503
BAD_REQUEST = 400
logger = logging.getLogger(__name__)


def services(request: Request) -> CopilotServices:
    bundle = getattr(request.app.state, SERVICES_STATE, None)
    if bundle is None:
        raise HTTPException(SERVICE_UNAVAILABLE, "The copilot is still loading its data; try again in a few seconds.")
    return bundle


def selection(request: Request) -> ModelSelection:
    return getattr(request.app.state, SELECTION_STATE)


def parse_as_of(as_of: str | None) -> datetime:
    """The demo clock from an ISO timestamp, defaulting to the configured demo moment.

    The data is naive, so a timestamp with an offset is converted to UTC and stripped; comparing aware with naive times
    would raise in every later request that reads the stored field inputs.
    """
    try:
        moment = datetime.fromisoformat(as_of or DEMO_AS_OF)
    except ValueError as error:
        raise HTTPException(BAD_REQUEST, f"as_of must be an ISO timestamp, got {as_of!r}") from error
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


def tools_at(request: Request, as_of: str | None) -> CopilotTools:
    return services(request).tools_at(parse_as_of(as_of))


def default_limiter() -> UsageLimiter:
    """The public demo's cap on Gemini calls, from the settings."""
    return UsageLimiter(UsageLimits(USAGE_LIMIT_PER_VISITOR, USAGE_LIMIT_TOTAL,
                                    timedelta(minutes=USAGE_LIMIT_WINDOW_MINUTES)))


def visitor_of(request: Request) -> str:
    """The caller's address: the last X-Forwarded-For entry behind Cloud Run, else the socket peer.

    Google's front end appends the address it saw to whatever the caller sent, so only the last entry is trustworthy;
    the first one is whatever the caller chose to write.
    """
    forwarded = request.headers.get(FORWARDED_FOR, "")
    last = forwarded.split(",")[-1].strip()
    return last or (request.client.host if request.client else UNKNOWN_VISITOR)


def model_call(request: Request) -> tuple[LimitDecision, str]:
    """Counts one Gemini-backed call against the caps; returns the decision and, when refused, the message."""
    limiter: UsageLimiter = getattr(request.app.state, LIMITER_STATE)
    visitor = visitor_of(request)
    decision = limiter.check(visitor, datetime.now(timezone.utc))
    logger.info("Model call by %s on %s: %s", visitor, request.url.path, "allowed" if decision.allowed else decision.scope)
    return decision, "" if decision.allowed else limit_message(decision, limiter.limits)


def require_model_call(request: Request) -> None:
    """Refuses with 429 and Retry-After when a cap is reached."""
    decision, message = model_call(request)
    if not decision.allowed:
        raise HTTPException(TOO_MANY_REQUESTS, message, headers={RETRY_AFTER: str(decision.retry_after_seconds)})
