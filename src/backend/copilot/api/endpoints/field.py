"""Field input endpoints: inspection photos for an alert, and supplier messages, read by Gemini into structured data.

Uploads arrive as base64 in JSON, which keeps the API simple for the browser and for tests.
Inputs and the alert are checked before a call is counted against the usage limit: a bad upload or an unknown alert
(404) never spends a visitor's quota. Model and schema failures come back as 502 with the reason.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from copilot.api.dependencies import parse_as_of, require_model_call, services
from copilot.core.errors import CopilotError, ImpactError
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
# A supplier email is a few hundred words; the cap keeps one request from sending a book to Gemini.
MAX_MESSAGE_CHARS = 20_000
MAX_ATTACHMENTS = 3


class Upload(BaseModel):
    mime_type: str
    data_base64: str


class InspectionRequest(Upload):
    as_of: str | None = None


class SupplierMessage(BaseModel):
    text: str = Field(default="", max_length=MAX_MESSAGE_CHARS)
    received_at: str
    attachments: list[Upload] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)


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
    photo, received_at = _attachment(body), parse_as_of(body.as_of)
    try:
        task = services(request).field.prepare_inspection(alert_id)
    except ImpactError as error:
        raise HTTPException(NOT_FOUND, str(error)) from error
    require_model_call(request)
    try:
        finding = await services(request).field.inspect(task, photo, received_at)
    except (LLMError, CopilotError) as error:
        raise HTTPException(BAD_GATEWAY, str(error)) from error
    return asdict(finding)


@router.get("/alerts/{alert_id}/inspections")
async def inspections(alert_id: str, request: Request, as_of: str | None = None) -> dict[str, object]:
    return {"inspections": services(request).field.findings_for(alert_id, parse_as_of(as_of))}


@router.post("/field/supplier-message")
async def supplier_message(body: SupplierMessage, request: Request) -> dict[str, object]:
    attachments, received_at = [_attachment(a) for a in body.attachments], parse_as_of(body.received_at)
    require_model_call(request)
    try:
        update = await services(request).field.read_supplier_message(body.text, attachments, received_at)
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
