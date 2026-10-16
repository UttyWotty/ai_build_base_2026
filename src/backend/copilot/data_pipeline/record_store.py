"""A small JSON file of records, for field inputs the copilot keeps: inspection findings and supplier updates.

Records are appended and read back as plain dicts; dataclasses are converted on the way in, and a caller may replace them all.
Like the proposal store, it is local state for the demo and would move to Firestore on Google Cloud.
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

FILE_ENCODING = "utf-8"
JSON_INDENT = 2
RECORDS_KEY = "records"


class RecordStore:
    """Records in one JSON file: appended one at a time, or replaced as a whole by the caller that owns them."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return list(json.loads(self.path.read_text(encoding=FILE_ENCODING)).get(RECORDS_KEY, []))

    def add(self, record: object) -> dict[str, object]:
        row = asdict(record) if is_dataclass(record) and not isinstance(record, type) else dict(record)  # type: ignore[arg-type]
        self._write(self.all() + [row])
        return json.loads(json.dumps(row, default=str))

    def replace(self, records: list[dict[str, object]]) -> int:
        """Overwrite the file with these rows and return how many were written."""
        self._write(list(records))
        return len(records)

    def clear(self) -> int:
        count = len(self.all())
        self._write([])
        return count

    def _write(self, records: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({RECORDS_KEY: records}, indent=JSON_INDENT, default=str) + "\n",
                             encoding=FILE_ENCODING)
