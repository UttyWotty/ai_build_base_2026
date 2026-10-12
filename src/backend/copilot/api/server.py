"""The copilot's HTTP API: FastAPI application with a lifespan that loads the services once.

Run locally with `make api` (uvicorn on port 8000), with the React dev server proxying /api to it. In the container
the same service also serves the built frontend, so the browser sees one origin and the agent stream is never buffered.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from copilot.api.dependencies import (
    LIMITER_STATE,
    SELECTION_STATE,
    SERVICES_STATE,
    default_limiter,
)
from copilot.api.endpoints import (
    agent,
    alerts,
    catalog,
    events,
    feedback,
    field,
    health,
    proposals,
    value,
)
from copilot.api.static_site import mount_frontend
from copilot.core.usage_limit import UsageLimiter
from copilot.services.factory import CopilotServices, default_services
from copilot.services.settings import FRONTEND_DIST_DIR, LOG_LEVEL
from llm_gateway.factory import default_selection

logger = logging.getLogger(__name__)
TITLE = "OSI API"
# The package logger every copilot module logs under; without a handler of its own its INFO lines were dropped.
COPILOT_LOGGER = "copilot"
LOG_FORMAT = "%(levelname)s:     %(name)s: %(message)s"


def configure_logging(level: str = LOG_LEVEL) -> None:
    """Sends the copilot's log lines to stderr, where Cloud Run collects them; safe to call more than once."""
    package = logging.getLogger(COPILOT_LOGGER)
    package.setLevel(level)
    if not package.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        package.addHandler(handler)
        package.propagate = False


def create_app(load_services: Callable[[], CopilotServices] = default_services,
               frontend_dir: Path = FRONTEND_DIST_DIR, limiter: UsageLimiter | None = None) -> FastAPI:
    """The application; tests pass their own service loader, frontend directory, and usage limiter."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setattr(app.state, SELECTION_STATE, default_selection())
        setattr(app.state, SERVICES_STATE, load_services())
        logger.info("Copilot services loaded; model %s", getattr(app.state, SELECTION_STATE).label)
        yield

    app = FastAPI(title=TITLE, lifespan=lifespan)
    setattr(app.state, LIMITER_STATE, limiter or default_limiter())
    for module in (health, catalog, alerts, events, field, feedback, proposals, value, agent):
        app.include_router(module.router)
    mount_frontend(app, frontend_dir)
    return app


configure_logging()
app = create_app()
