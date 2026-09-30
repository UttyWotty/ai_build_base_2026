"""Re-exports the shared language model contract and adapters for this package's services and tests.

The implementations live in llm_gateway, so every package selects Gemini or a local model the same way.
build_llm_client() returns the configured client; nothing is sent until a question is asked.
"""
from llm_gateway import LLMClient, LLMError, build_llm_client
from llm_gateway.openai_compatible import OpenAICompatibleClient

__all__ = ["LLMClient", "LLMError", "OpenAICompatibleClient", "build_llm_client"]
