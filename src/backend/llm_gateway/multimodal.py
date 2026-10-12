"""Structured reading of images and documents: an instruction, text, and attachments in; JSON that follows a schema out.

Only Gemini reads images and PDFs here; the local provider raises LLMError with a clear message instead of guessing.
Retries follow the same policy as chat completion, and a reply that is not valid JSON is reported, never repaired.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx
from google import genai
from google.genai import errors, types

from llm_gateway.client import LLMError
from llm_gateway.retry import RetryPolicy, is_transient
from llm_gateway.selection import ModelSelection, Provider

JSON_MIME = "application/json"
TEMPERATURE = 0.0
MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True)
class Attachment:
    """An image or document to read."""

    mime_type: str
    data: bytes


class StructuredReader(Protocol):
    """Anything that reads text and attachments into JSON following a schema."""

    def read(self, instruction: str, text: str, attachments: Sequence[Attachment], schema: dict[str, object]) -> dict: ...


class GeminiReader:
    """Structured reading on a Gemini model."""

    def __init__(self, model: str, timeout_seconds: float, retry_policy: RetryPolicy = RetryPolicy(),
                 client: genai.Client | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy
        self.sleep = sleep
        self._client = client

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            try:
                self._client = genai.Client(
                    http_options=types.HttpOptions(timeout=int(self.timeout_seconds * MILLISECONDS_PER_SECOND)))
            except ValueError as error:
                raise LLMError(f"Gemini is not configured: {error}") from error
        return self._client

    def read(self, instruction: str, text: str, attachments: Sequence[Attachment], schema: dict[str, object]) -> dict:
        parts = [types.Part.from_bytes(data=a.data, mime_type=a.mime_type) for a in attachments]
        if text:
            parts.append(types.Part(text=text))
        config = types.GenerateContentConfig(system_instruction=instruction, temperature=TEMPERATURE,
                                             response_mime_type=JSON_MIME, response_json_schema=schema)
        reply = self._generate([types.Content(role="user", parts=parts)], config)
        try:
            return dict(json.loads(reply))
        except (ValueError, TypeError) as error:
            raise LLMError(f"Gemini {self.model} returned text that is not JSON: {reply[:120]!r}") from error

    def _generate(self, contents: list[types.Content], config: types.GenerateContentConfig) -> str:
        failure: Exception | None = None
        for attempt in range(self.retry_policy.retries + 1):
            if attempt:
                self.sleep(self.retry_policy.delay_before(attempt))
            try:
                response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
            except errors.APIError as error:
                failure = error
                if not is_transient(error.code):
                    break
                continue
            except httpx.HTTPError as error:
                failure = error
                continue
            if response.text:
                return response.text
            raise LLMError(f"Gemini {self.model} returned no content")
        raise LLMError(f"Gemini {self.model} request failed: {failure}") from failure


class UnsupportedReader:
    """Stands in for providers that cannot read images or documents."""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    def read(self, instruction: str, text: str, attachments: Sequence[Attachment], schema: dict[str, object]) -> dict:
        raise LLMError(f"Reading photos and documents needs Gemini; the configured provider is {self.provider}.")


def build_reader(selection: ModelSelection) -> StructuredReader:
    """A reader for the selection: Gemini reads, other providers explain why they cannot."""
    if selection.provider is Provider.GEMINI:
        return GeminiReader(selection.model, selection.timeout_seconds)
    return UnsupportedReader(selection.provider.value)
