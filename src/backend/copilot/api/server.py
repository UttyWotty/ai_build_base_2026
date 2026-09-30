"""The copilot's HTTP API: FastAPI application with a lifespan that loads the services once.

Run locally with `make api` (uvicorn on port 8000). The React frontend calls it under /api; in production Firebase
Hosting forwards /api to this service on Cloud Run, so the browser sees one origin.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from copilot.api.dependencies import SELECTION_STATE, SERVICES_STATE
from copilot.api.endpoints import agent, alerts, catalog, health, proposals
from copilot.services.factory import CopilotServices, default_services
from llm_gateway.factory import default_selection

logger = logging.getLogger(__name__)
TITLE = "emoldinounited API"


def create_app(load_services: Callable[[], CopilotServices] = default_services) -> FastAPI:
    """The application; tests pass their own service loader."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setattr(app.state, SELECTION_STATE, default_selection())
        setattr(app.state, SERVICES_STATE, load_services())
        logger.info("Copilot services loaded; model %s", getattr(app.state, SELECTION_STATE).label)
        yield

    app = FastAPI(title=TITLE, lifespan=lifespan)
    for module in (health, catalog, alerts, proposals, agent):
        app.include_router(module.router)
    return app


app = create_app()
