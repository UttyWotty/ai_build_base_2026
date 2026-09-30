"""Filesystem adapter for action proposals: the agent adds them as pending, and a person approves or rejects them.

Proposals live in one JSON file so the web app and the command line see the same queue.
Status changes rewrite the file; nothing here ever executes an action.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from copilot.core.agent_views import ActionProposal
from copilot.core.errors import CopilotError

FILE_ENCODING = "utf-8"
JSON_INDENT = 2
PROPOSALS_KEY = "proposals"
ALLOWED_STATUSES = frozenset({"pending", "approved", "rejected"})


class ProposalStoreError(CopilotError):
    """A proposal id or status is not valid."""


class ProposalStore:
    """Reads and writes the proposal queue."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return list(json.loads(self.path.read_text(encoding=FILE_ENCODING)).get(PROPOSALS_KEY, []))

    def next_id(self, alert_id: str) -> str:
        return f"PR-{alert_id}-{sum(1 for p in self.all() if p['alert_id'] == alert_id) + 1}"

    def add(self, proposal: ActionProposal) -> dict[str, object]:
        record = asdict(proposal)
        self._write(self.all() + [record])
        return record

    def set_status(self, proposal_id: str, status: str) -> dict[str, object]:
        if status not in ALLOWED_STATUSES:
            raise ProposalStoreError(f"Unknown status {status!r}")
        proposals = self.all()
        for record in proposals:
            if record["proposal_id"] == proposal_id:
                record["status"] = status
                self._write(proposals)
                return record
        raise ProposalStoreError(f"Unknown proposal {proposal_id}")

    def clear(self) -> int:
        """Remove every proposal; return how many there were."""
        count = len(self.all())
        self._write([])
        return count

    def _write(self, proposals: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({PROPOSALS_KEY: proposals}, indent=JSON_INDENT, default=str) + "\n",
                             encoding=FILE_ENCODING)
