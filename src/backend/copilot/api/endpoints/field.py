"""Field input endpoints: inspection photos for an alert, and supplier messages, read by Gemini into structured data.

Uploads arrive as base64 in JSON, which keeps the API simple for the browser and for tests.
Model and schema failures come back as 502 with the reason, so the app can show what went wrong.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from copilot.api.dependencies import parse_as_of, require_model_call, services
from copilot.core.errors import CopilotError
from copilot.data_pipeline.field_samples import (
    photo_path,
    sample_messages,
    sample_photos,
)
from copilot.services.settings import FIELD_SAMPLES_DIR
from llm_gateway.client import LLMError
from llm_gateway.multimodal import Attachment

router = APIRouter(prefix="/api")
BAD_REQUEST, NOT_FOUND, BAD_GATEWAY = 400, 404, 502
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class Upload(BaseModel):
    mime_type: str
    data_base64: str


class InspectionRequest(Upload):
    as_of: str | None = None


class SupplierMessage(BaseModel):
    text: str = ""
    received_at: str
    attachments: list[Upload] = []


def _attachment(upload: Upload) -> Attachment:
    try:
        data = base64.b64decode(upload.data_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(BAD_REQUEST, "The upload is not valid base64") from error
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(BAD_REQUEST, "The upload is larger than 8 MB")
    return Attachment(upload.mime_type, data)


@router.get("/field/samples")
async def samples() -> dict[str, object]:
    return {"messages": [asdict(m) for m in sample_messages(FIELD_SAMPLES_DIR)],
            "photos": [asdict(p) for p in sample_photos(FIELD_SAMPLES_DIR)]}


@router.get("/field/samples/photos/{name}")
async def sample_photo(name: str) -> FileResponse:
    path = photo_path(FIELD_SAMPLES_DIR, name)
    if path is None:
        raise HTTPException(NOT_FOUND, f"No sample photo {name}")
    return FileResponse(path)


@router.post("/alerts/{alert_id}/inspection")
async def inspect(alert_id: str, body: InspectionRequest, request: Request) -> dict[str, object]:
    require_model_call(request)
    try:
        finding = services(request).field.inspect(alert_id, _attachment(body), parse_as_of(body.as_of))
    except (LLMError, CopilotError) as error:
        raise HTTPException(BAD_GATEWAY, str(error)) from error
    return asdict(finding)


@router.get("/alerts/{alert_id}/inspections")
async def inspections(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    return {"inspections": services(request).field.findings_for(alert_id, parse_as_of(as_of))}


@router.post("/field/supplier-message")
async def supplier_message(body: SupplierMessage, request: Request) -> dict[str, object]:
    require_model_call(request)
    try:
        update = services(request).field.read_supplier_message(body.text, [_attachment(a) for a in body.attachments],
                                                               parse_as_of(body.received_at))
    except (LLMError, CopilotError) as error:
        raise HTTPException(BAD_GATEWAY, str(error)) from error
    return asdict(update)


@router.get("/field/supplier-updates")
async def supplier_updates(request: Request, as_of: str | None = None) -> dict[str, object]:
    return {"updates": [asdict(u) for u in services(request).field.updates_known(parse_as_of(as_of))]}


@router.post("/field/reset")
async def reset(request: Request) -> dict[str, int]:
    bundle = services(request)
    return {"removed": bundle.field.inspections.clear() + bundle.field.updates.clear() + bundle.feedback.clear()}
