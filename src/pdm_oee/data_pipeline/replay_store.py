"""Filesystem adapter for the saved alert replay: every alert of the test period with its outcome and backtest truth.

The alerts command writes it and the investigation tools read it, so tools never re-run the backtest.
A missing replay reads as no alerts.
"""
from __future__ import annotations

import json
from pathlib import Path

JSON_INDENT = 2
FILE_ENCODING = "utf-8"
ALERTS_KEY = "alerts"


def write_replay(replay: dict[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(replay, indent=JSON_INDENT, default=str) + "\n", encoding=FILE_ENCODING)
    return path


def read_replay_alerts(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding=FILE_ENCODING)).get(ALERTS_KEY, []))
