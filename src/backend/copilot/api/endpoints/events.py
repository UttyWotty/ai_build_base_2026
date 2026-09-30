"""The event feed endpoint: what happened in the plant and its spares between two moments.

Live mode polls it as the demo clock runs; the window is capped so a request stays small.
Times are ISO timestamps; the end must not be before the start.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request

from copilot.api.dependencies import parse_as_of, services
from copilot.services.event_feed import EventFeed

router = APIRouter(prefix="/api")
MAX_WINDOW = timedelta(days=31)
BAD_REQUEST = 400
TIME_FORMAT = "%Y-%m-%dT%H:%M"


@router.get("/events")
async def events(request: Request, start: str, end: str) -> dict[str, object]:
    first, last = parse_as_of(start), parse_as_of(end)
    if last < first or last - first > MAX_WINDOW:
        raise HTTPException(BAD_REQUEST, "The window must run forward and span at most 31 days")
    bundle = services(request)
    feed = EventFeed(bundle.impact, getattr(bundle, "outcomes", None)).between(first, last)
    return {"events": [{"at": e.at.strftime(TIME_FORMAT), "kind": e.kind, "site_id": e.site_id, "subject": e.subject,
                        "title": e.title, "severity": e.severity.value, "alert_id": e.alert_id} for e in feed]}
