"""Proposal endpoints: list the plans the agent drafted, and record a person's approval or rejection.

Only the status changes here; the numbers were fixed from the impact analysis when the proposal was made.
An unknown proposal or status comes back as 400 with the store's message.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from copilot.api.dependencies import services
from copilot.data_pipeline.proposal_store import ProposalStoreError

router = APIRouter(prefix="/api/proposals")
BAD_REQUEST = 400


class StatusChange(BaseModel):
    """The decision a person made."""

    status: str


@router.get("")
async def list_proposals(request: Request) -> dict[str, object]:
    return {"proposals": list(reversed(services(request).proposals.all()))}


@router.post("/{proposal_id}/status")
async def set_status(proposal_id: str, change: StatusChange, request: Request) -> dict[str, object]:
    try:
        return services(request).proposals.set_status(proposal_id, change.status)
    except ProposalStoreError as error:
        raise HTTPException(BAD_REQUEST, str(error)) from error
