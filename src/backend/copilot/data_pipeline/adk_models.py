"""Turns a model selection from the gateway into the model object the Agent Development Kit expects.

Gemini is passed by name, and ADK reaches it through google-genai with the same credentials as the gateway.
A local OpenAI-compatible server is wrapped in ADK's LiteLlm adapter.
"""
from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm

from llm_gateway.selection import ModelSelection, Provider

LITELLM_OPENAI_PREFIX = "openai/"
# Local servers ignore the key, but the OpenAI client refuses to send a request without one.
LOCAL_API_KEY = "local"


def adk_model(selection: ModelSelection) -> str | LiteLlm:
    """The ADK model for a selection."""
    if selection.provider is Provider.GEMINI:
        return selection.model
    return LiteLlm(model=LITELLM_OPENAI_PREFIX + selection.model, api_base=selection.base_url, api_key=LOCAL_API_KEY,
                   timeout=selection.timeout_seconds)
