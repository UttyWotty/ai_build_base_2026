"""Converts OpenAI-style chat messages into the Gemini request shape: one system instruction plus turns.

System messages are joined into the system instruction; assistant turns become the model role.
The conversion is pure so its rules are tested without a network call.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

SYSTEM_ROLE = "system"
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
GEMINI_MODEL_ROLE = "model"
SYSTEM_SEPARATOR = "\n\n"


class MessageFormatError(ValueError):
    """A chat message has an unknown role or no content."""


@dataclass(frozen=True)
class GeminiTurn:
    """One conversation turn in Gemini's role vocabulary."""

    role: str
    text: str


@dataclass(frozen=True)
class GeminiRequest:
    """The system instruction (empty when absent) and the conversation turns."""

    system_instruction: str
    turns: tuple[GeminiTurn, ...]


def to_gemini_request(messages: Sequence[dict[str, str]]) -> GeminiRequest:
    """Split system messages from the conversation and map roles; consecutive same-role turns stay separate."""
    system_parts: list[str] = []
    turns: list[GeminiTurn] = []
    for message in messages:
        role, content = message.get("role"), message.get("content")
        if not isinstance(content, str):
            raise MessageFormatError(f"Message without text content: {message!r}")
        if role == SYSTEM_ROLE:
            system_parts.append(content)
        elif role == USER_ROLE:
            turns.append(GeminiTurn(USER_ROLE, content))
        elif role == ASSISTANT_ROLE:
            turns.append(GeminiTurn(GEMINI_MODEL_ROLE, content))
        else:
            raise MessageFormatError(f"Unknown message role {role!r}")
    if not turns:
        raise MessageFormatError("A request needs at least one user or assistant message")
    return GeminiRequest(SYSTEM_SEPARATOR.join(system_parts), tuple(turns))
