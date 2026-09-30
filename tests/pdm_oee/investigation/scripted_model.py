"""A scripted stand-in for the language model: canned replies in order, recording every message list it receives.

An exception placed in the script is raised instead of returned, to simulate an unreachable server.
Running out of replies fails the test loudly.
"""
from __future__ import annotations

from collections.abc import Sequence


class ScriptedModel:
    def __init__(self, replies: Sequence[object]) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        self.calls.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return str(reply)
