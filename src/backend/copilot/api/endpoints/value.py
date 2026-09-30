"""The track record endpoint: the copilot's recommendations scored against what really happened.

The backtest runs once per service and is cached, so repeated calls are instant.
It does not depend on the demo clock; it covers the whole test period.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from copilot.api.dependencies import services
from copilot.core.value_views import track_record_result

router = APIRouter(prefix="/api")


@router.get("/value")
async def value(request: Request) -> dict[str, object]:
    cases, summary = services(request).value.track_record()
    return track_record_result(cases, summary)
