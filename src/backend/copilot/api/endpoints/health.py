"""Health and diagnostics: a lightweight health check for Cloud Run, and an engine status that reports readiness.

/health reads configuration only and never touches data or the model, so probes stay cheap.
/api/engine-status says whether the services finished loading and which model the agent uses.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from copilot.api.dependencies import SELECTION_STATE, SERVICES_STATE

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/engine-status")
async def engine_status(request: Request) -> dict[str, object]:
    selection = getattr(request.app.state, SELECTION_STATE)
    return {"ready": getattr(request.app.state, SERVICES_STATE, None) is not None,
            "model": selection.label, "provider": selection.provider.value}
