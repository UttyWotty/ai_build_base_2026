"""Shared language model gateway: one setting chooses Gemini or a local OpenAI-compatible model for every package.

Every package depends only on the LLMClient protocol (chat messages in, reply text out) and builds clients here.
The gateway sits below the component packages and the copilot, and imports none of them.
"""
from llm_gateway.client import LLMClient, LLMError
from llm_gateway.factory import build_llm_client
from llm_gateway.selection import ModelSelection, Provider, resolve_selection
