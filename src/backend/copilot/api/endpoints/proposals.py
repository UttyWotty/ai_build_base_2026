"""Proposal endpoints: list the drafted plans, record a person's decision, report outcomes, and reset the demo.

Only the status changes here; the numbers were fixed from the impact analysis when the proposal was made.
Approved proposals become decisions; their outcomes settle as the demo clock passes the real events.
An unknown proposal or status comes back as 400 with the store's message.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from copilot.api.dependencies import parse_as_of, services
from copilot.data_pipeline.proposal_store import ProposalStoreError

router = APIRouter(prefix="/api/proposals")
BAD_REQUEST = 400
TIME_FORMAT = "%Y-%m-%dT%H:%M"


class StatusChange(BaseModel):
    """The decision a person made."""

    status: str


@router.get("")
async def list_proposals(request: Request) -> dict[str, object]:
    return {"proposals": list(reversed(services(request).proposals.all()))}


@router.get("/outcomes")
async def outcomes(request: Request, as_of: str | None = None) -> dict[str, object]:
    """Each approved decision's outcome as it stands at the demo clock (pending until it settles)."""
    settled = services(request).outcomes.outcomes(parse_as_of(as_of))
    return {"outcomes": [{"proposal_id": o.proposal_id, "alert_id": o.alert_id, "status": o.status.value,
                          "settled_at": o.settled_at.strftime(TIME_FORMAT) if o.settled_at else None,
                          "with_plan_hours": o.with_plan.lost_hours if o.with_plan else None,
                          "without_plan_hours": o.without_plan.lost_hours if o.without_plan else None,
                          "hours_saved": o.hours_saved, "usd_saved": o.usd_saved,
                          "extra_cost_usd": o.with_plan.extra_cost_usd if o.with_plan else None} for o in settled]}


@router.post("/reset")
async def reset(request: Request) -> dict[str, int]:
    """Clear every proposal, to start a demo from a clean state."""
    return {"removed": services(request).proposals.clear()}


@router.post("/{proposal_id}/status")
async def set_status(proposal_id: str, change: StatusChange, request: Request) -> dict[str, object]:
    try:
        return services(request).proposals.set_status(proposal_id, change.status)
    except ProposalStoreError as error:
        raise HTTPException(BAD_REQUEST, str(error)) from error
