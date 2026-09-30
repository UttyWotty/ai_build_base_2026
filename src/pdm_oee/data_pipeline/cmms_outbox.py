"""Filesystem adapter for the simulated CMMS outbox: draft work orders waiting for a person to approve or dismiss them.

Nothing leaves this file; approving a draft only changes its status here. The outbox is one JSON document so the UI and
the command line see the same drafts. Unknown draft ids and statuses are refused.
"""
from __future__ import annotations

import json
from pathlib import Path

DRAFT, APPROVED, DISMISSED = "draft", "approved", "dismissed"
STATUSES = frozenset({DRAFT, APPROVED, DISMISSED})
JSON_INDENT = 2
FILE_ENCODING = "utf-8"


class OutboxError(Exception):
    """A status change the outbox cannot apply."""


def write_outbox(drafts: list[dict[str, object]], path: Path) -> Path:
    """Replace the outbox with these drafts, each starting in the draft status."""
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [{**draft, "status": DRAFT} for draft in drafts]
    path.write_text(json.dumps(records, indent=JSON_INDENT, default=str) + "\n", encoding=FILE_ENCODING)
    return path


def read_outbox(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding=FILE_ENCODING)) if path.exists() else []


def set_status(path: Path, alert_id: str, status: str) -> dict[str, object]:
    """Approve or dismiss one draft; returns the updated record."""
    if status not in STATUSES:
        raise OutboxError(f"Unknown status '{status}'")
    records = read_outbox(path)
    for record in records:
        if record["alert_id"] == alert_id:
            record["status"] = status
            path.write_text(json.dumps(records, indent=JSON_INDENT, default=str) + "\n", encoding=FILE_ENCODING)
            return record
    raise OutboxError(f"No draft '{alert_id}' in the outbox")
