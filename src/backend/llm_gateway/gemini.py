"""Adapter for Gemini through the google-genai SDK, on the Gemini Developer API or Vertex AI.

Credentials and backend come from the SDK's own environment: GEMINI_API_KEY for AI Studio, or the Vertex AI
project, location, and service account on Google Cloud. Rate limits and server errors are retried with backoff.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence

import httpx
from google import genai
from google.genai import errors, types

from llm_gateway.client import LLMError
from llm_gateway.messages import MessageFormatError, to_gemini_request
from llm_gateway.retry import RetryPolicy, is_transient

DEFAULT_TEMPERATURE = 0.0
# Room for the reply plus the model's internal reasoning, which counts against the same budget.
DEFAULT_MAX_OUTPUT_TOKENS = 8192
MILLISECONDS_PER_SECOND = 1000


class GeminiClient:
    """Chat completion on a Gemini model."""

    def __init__(
        self, model: str, timeout_seconds: float, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE, retry_policy: RetryPolicy = RetryPolicy(),
        client: genai.Client | None = None, sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.retry_policy = retry_policy
        self.sleep = sleep
        self.timeout_seconds = timeout_seconds
        self._client = client

    @property
    def client(self) -> genai.Client:
        """The SDK client, created on first use so a missing key fails a request, not an import."""
        if self._client is None:
            try:
                self._client = genai.Client(
                    http_options=types.HttpOptions(timeout=int(self.timeout_seconds * MILLISECONDS_PER_SECOND)))
            except ValueError as error:
                raise LLMError(f"Gemini is not configured: {error}") from error
        return self._client

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        try:
            request = to_gemini_request(messages)
        except MessageFormatError as error:
            raise LLMError(str(error)) from error
        contents = [types.Content(role=t.role, parts=[types.Part(text=t.text)]) for t in request.turns]
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction or None,
            temperature=self.temperature, max_output_tokens=self.max_output_tokens)
        return self._generate_with_retries(contents, config)

    def _generate_with_retries(self, contents: list[types.Content], config: types.GenerateContentConfig) -> str:
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
            raise LLMError(f"Gemini {self.model} returned no text (finish: {_finish_reason(response)})")
        raise LLMError(f"Gemini {self.model} request failed: {failure}") from failure


def _finish_reason(response: types.GenerateContentResponse) -> str:
    candidates = response.candidates or []
    return str(candidates[0].finish_reason) if candidates else "no candidates"
