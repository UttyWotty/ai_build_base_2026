"""Operator feedback endpoints: mark an alert as false with a reason, undo it, and read what operators said about an alert.

An alert shows its own verdicts and those on earlier alerts of the same asset and failure mode, with a caution note.
Unknown alerts are 404; a missing reason, or a verdict before the alert was raised, is 400.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from copilot.api.dependencies import parse_as_of, services
from copilot.core.alert_feedback import feedback_row, view_dict
from copilot.core.errors import FeedbackError, ImpactError

router = APIRouter(prefix="/api")
BAD_REQUEST, NOT_FOUND = 400, 404
MAX_REASON_CHARS = 1_000


class FalseAlertRequest(BaseModel):
    """A false-alert verdict at the demo clock."""

    reason: str = Field(max_length=MAX_REASON_CHARS)
    as_of: str | None = None


@router.post("/alerts/{alert_id}/feedback")
async def mark_false(alert_id: str, body: FalseAlertRequest, request: Request) -> dict[str, object]:
    try:
        feedback = services(request).feedback.mark_false(alert_id, body.reason, parse_as_of(body.as_of))
    except ImpactError as error:
        raise HTTPException(NOT_FOUND, str(error)) from error
    except FeedbackError as error:
        raise HTTPException(BAD_REQUEST, str(error)) from error
    return feedback_row(feedback)


@router.get("/alerts/{alert_id}/feedback")
async def feedback(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    try:
        return view_dict(services(request).feedback.view(alert_id, parse_as_of(as_of)))
    except ImpactError as error:
        raise HTTPException(NOT_FOUND, str(error)) from error


@router.delete("/alerts/{alert_id}/feedback")
async def withdraw(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    """Undo this alert's own verdicts known at the clock; repeating it removes nothing and still succeeds."""
    try:
        removed = services(request).feedback.withdraw(alert_id, parse_as_of(as_of))
    except ImpactError as error:
        raise HTTPException(NOT_FOUND, str(error)) from error
    return {"alert_id": alert_id, "removed": removed}
