"""Tests that the factory builds the adapter matching the selected provider.

Building a client sends nothing and needs no credentials; Gemini's SDK client is created on first use.
The local adapter receives the selection's endpoint and model.
"""
from __future__ import annotations

from llm_gateway.factory import build_llm_client
from llm_gateway.gemini import GeminiClient
from llm_gateway.openai_compatible import OpenAICompatibleClient
from llm_gateway.selection import ModelSelection, Provider


def test_gemini_selection_builds_the_gemini_adapter_without_credentials() -> None:
    client = build_llm_client(ModelSelection(Provider.GEMINI, "gemini-x", "unused", 5.0))
    assert isinstance(client, GeminiClient) and client.model == "gemini-x"


def test_local_selection_builds_the_openai_compatible_adapter() -> None:
    client = build_llm_client(ModelSelection(Provider.LOCAL, "local-y", "http://127.0.0.1:9/v1/", 5.0))
    assert isinstance(client, OpenAICompatibleClient)
    assert client.url == "http://127.0.0.1:9/v1/chat/completions" and client.model == "local-y"
