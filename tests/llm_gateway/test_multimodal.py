"""Tests for the structured reader: the request carries the attachments and the schema, JSON replies are parsed, and
non-JSON replies and non-Gemini providers fail with a clear LLMError.

The Gemini SDK is replaced by an in-memory fake; no request leaves the machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from google.genai import types

from llm_gateway.client import LLMError
from llm_gateway.multimodal import Attachment, GeminiReader, build_reader
from llm_gateway.selection import ModelSelection, Provider

SCHEMA = {"type": "object", "properties": {"change": {"type": "string"}}}


@dataclass
class FakeModels:
    reply: str
    calls: list[dict] = field(default_factory=list)

    def generate_content(self, model, contents, config):
        self.calls.append({"contents": contents, "config": config})
        return types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text=self.reply)]))])


@dataclass
class FakeClient:
    models: FakeModels


def test_request_carries_attachments_text_and_schema() -> None:
    models = FakeModels('{"change": "delay"}')
    reader = GeminiReader("gemini-x", 5.0, client=FakeClient(models))
    assert reader.read("Read it.", "Order late", [Attachment("image/png", b"png")], SCHEMA) == {"change": "delay"}
    call = models.calls[0]
    parts = call["contents"][0].parts
    assert parts[0].inline_data.mime_type == "image/png" and parts[1].text == "Order late"
    assert call["config"].response_json_schema == SCHEMA and call["config"].response_mime_type == "application/json"


def test_non_json_replies_and_other_providers_fail_clearly() -> None:
    reader = GeminiReader("gemini-x", 5.0, client=FakeClient(FakeModels("not json")))
    with pytest.raises(LLMError, match="not JSON"):
        reader.read("Read it.", "text", [], SCHEMA)
    with pytest.raises(LLMError, match="needs Gemini"):
        build_reader(ModelSelection(Provider.LOCAL, "qwen", "", 5.0)).read("x", "y", [], SCHEMA)
