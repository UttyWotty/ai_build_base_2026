"""Static reference for the frontend: the named demo scenarios and the default demo clock.

Scenarios are defined once in the copilot core and shared with the other interfaces.
Nothing here loads data.
"""
from __future__ import annotations

from fastapi import APIRouter

from copilot.core.impact_summary import SCENARIOS
from copilot.services.settings import DEMO_AS_OF

TIME_FORMAT = "%Y-%m-%dT%H:%M"
router = APIRouter(prefix="/api")


@router.get("/scenarios")
async def scenarios() -> dict[str, object]:
    return {"default_as_of": DEMO_AS_OF,
            "scenarios": [{"id": s.scenario_id, "label": s.label, "as_of": s.as_of.strftime(TIME_FORMAT), "story": s.story}
                          for s in SCENARIOS]}
