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

from copilot.api.dependencies import SELECTION_STATE, SERVICES_STATE
from copilot.api.endpoints import (
    agent,
    alerts,
    catalog,
    events,
    field,
    health,
    proposals,
    value,
)
from copilot.api.static_site import mount_frontend
from copilot.services.factory import CopilotServices, default_services
from copilot.services.settings import FRONTEND_DIST_DIR
from llm_gateway.factory import default_selection

logger = logging.getLogger(__name__)
TITLE = "emoldinounited API"


def create_app(load_services: Callable[[], CopilotServices] = default_services,
               frontend_dir: Path = FRONTEND_DIST_DIR) -> FastAPI:
    """The application; tests pass their own service loader and frontend directory."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setattr(app.state, SELECTION_STATE, default_selection())
        setattr(app.state, SERVICES_STATE, load_services())
        logger.info("Copilot services loaded; model %s", getattr(app.state, SELECTION_STATE).label)
        yield

    app = FastAPI(title=TITLE, lifespan=lifespan)
    for module in (health, catalog, alerts, events, field, proposals, value, agent):
        app.include_router(module.router)
    mount_frontend(app, frontend_dir)
    return app


app = create_app()
