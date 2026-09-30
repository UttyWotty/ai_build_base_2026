"""A scripted stand-in for the language model, shared by the service tests.

It returns canned replies in order and records every message list it receives.
An exception placed in the script is raised instead of returned, to simulate an unreachable model.
"""
from __future__ import annotations

from collections.abc import Sequence


class ScriptedModel:
    """Replies from a script; an exception in the script is raised instead."""

    def __init__(self, replies: Sequence[object]) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        self.calls.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return str(reply)
