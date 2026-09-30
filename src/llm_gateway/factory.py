"""Builds the LLMClient for a model selection, and the default selection from the shared settings.

Callers that accept a per-run provider, model, or endpoint pass them to default_selection as overrides.
This is the only module that knows which adapter class serves which provider.
"""
from __future__ import annotations

from llm_gateway import settings
from llm_gateway.client import LLMClient
from llm_gateway.gemini import GeminiClient
from llm_gateway.openai_compatible import OpenAICompatibleClient
from llm_gateway.selection import (
    ModelDefaults,
    ModelSelection,
    Provider,
    resolve_selection,
)


def settings_defaults() -> ModelDefaults:
    """The model defaults read from the environment at import time."""
    return ModelDefaults(settings.LLM_PROVIDER, settings.GEMINI_MODEL, settings.LLM_MODEL, settings.LLM_BASE_URL,
                         settings.LLM_TIMEOUT_SECONDS)


def default_selection(provider: str | None = None, model: str | None = None,
                      base_url: str | None = None) -> ModelSelection:
    """The configured selection with optional per-run overrides."""
    return resolve_selection(settings_defaults(), provider, model, base_url)


def build_llm_client(selection: ModelSelection | None = None) -> LLMClient:
    """A client for the selection, or for the configured default."""
    chosen = selection or default_selection()
    if chosen.provider is Provider.GEMINI:
        return GeminiClient(chosen.model, chosen.timeout_seconds)
    return OpenAICompatibleClient(chosen.base_url, chosen.model, chosen.timeout_seconds)
