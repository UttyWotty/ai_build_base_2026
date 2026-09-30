"""The contract every language model adapter fulfils: chat messages in, reply text out.

Messages are dicts with a role (system, user, or assistant) and a content string, in OpenAI chat format.
Adapters raise LLMError whenever the endpoint cannot produce a reply, so services handle one error type.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class LLMError(Exception):
    """The language model endpoint could not produce a reply."""


class LLMClient(Protocol):
    """Anything that turns chat messages into reply text."""

    def complete(self, messages: Sequence[dict[str, str]]) -> str: ...
