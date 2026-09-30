"""Adapter for an OpenAI-compatible chat completion endpoint, such as a local mlx_lm or mlx_vlm server.

The LLMClient protocol is all the services depend on, so tests pass a stub and production passes this HTTP client.
Requests use temperature 0 so the same prompt gives the same reply; transport failures raise LLMError.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import httpx

CHAT_PATH = "/chat/completions"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 800
# One extra attempt absorbs a transient failure of a shared local server; a second failure is reported.
DEFAULT_TRANSPORT_RETRIES = 1


class LLMError(Exception):
    """The language model endpoint could not produce a reply."""


class LLMClient(Protocol):
    """Anything that turns chat messages into reply text."""

    def complete(self, messages: Sequence[dict[str, str]]) -> str: ...


class OpenAICompatibleClient:
    """HTTP client for /chat/completions."""

    def __init__(
        self, base_url: str, model: str, timeout_seconds: float,
        max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE,
        transport_retries: int = DEFAULT_TRANSPORT_RETRIES,
    ) -> None:
        self.url = base_url.rstrip("/") + CHAT_PATH
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.transport_retries = transport_retries

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        payload = {"model": self.model, "messages": list(messages),
                   "temperature": self.temperature, "max_tokens": self.max_tokens}
        failure: Exception | None = None
        for _ in range(self.transport_retries + 1):
            try:
                response = httpx.post(self.url, json=payload, timeout=self.timeout_seconds)
                response.raise_for_status()
                return str(response.json()["choices"][0]["message"]["content"])
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
                failure = error
        raise LLMError(f"Language model request to {self.url} failed: {failure}") from failure
