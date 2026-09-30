"""Alert endpoints at a demo clock: the open alerts with the headline numbers, one alert's impact, and its evidence.

Each call binds the tools to the requested time, so every number is point-in-time.
Unknown alerts come back as 404 with the tool's message.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from copilot.api.dependencies import tools_at
from copilot.core.impact_summary import avoided, conflict_note, headline, recommended

router = APIRouter(prefix="/api")
NOT_FOUND = 404
ERROR_KEY = "error"


@router.get("/overview")
async def overview(request: Request, as_of: str | None = None) -> dict[str, object]:
    """Open alerts with their recommended option, and the headline across them."""
    tools = tools_at(request, as_of)
    listing = tools.list_open_alerts()
    impacts = [tools.analyse_alert_impact(a["alert_id"]) for a in listing["alerts"]]
    rows = []
    for alert, impact in zip(listing["alerts"], impacts):
        hours, cost = avoided(impact)
        rows.append({**alert, "recommended": recommended(impact), "conflict": conflict_note(impact),
                     "downtime_avoided_hours": hours, "cost_avoided_usd": cost})
    return {"as_of": listing["as_of"], "headline": headline(impacts), "alerts": rows}


@router.get("/alerts/{alert_id}/impact")
async def impact(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    tools = tools_at(request, as_of)
    result = _checked(tools.safe(tools.analyse_alert_impact)(alert_id))
    return {**result, "conflict": conflict_note(result)}


@router.get("/alerts/{alert_id}/evidence")
async def evidence(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    tools = tools_at(request, as_of)
    return _checked(tools.safe(tools.get_sensor_evidence)(alert_id))


def _checked(result: dict[str, object]) -> dict[str, object]:
    if ERROR_KEY in result:
        raise HTTPException(NOT_FOUND, str(result[ERROR_KEY]))
    return result
