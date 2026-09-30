"""Reads the demo's sample field inputs: supplier messages (text with headers) and inspection photos.

Messages carry From, Date, and Subject headers; the Date header is when the message counts as received.
Photos are listed with the asset id their file name starts with, so the app can offer them on the right alert.
"""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

INBOX_DIR = "inbox"
PHOTOS_DIR = "photos"
PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
HEADER_SEPARATOR = ":"
ASSET_SEPARATOR = "_"


@dataclass(frozen=True)
class SampleMessage:
    name: str
    sender: str
    received_at: str
    subject: str
    text: str


@dataclass(frozen=True)
class SamplePhoto:
    name: str
    asset_id: str
    mime_type: str


def sample_messages(samples_dir: Path) -> list[SampleMessage]:
    messages = []
    for path in sorted((samples_dir / INBOX_DIR).glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        head, _, _ = text.partition("\n\n")
        headers = {k.strip().lower(): v.strip() for k, _, v in (line.partition(HEADER_SEPARATOR) for line in head.splitlines())}
        messages.append(SampleMessage(path.stem, headers.get("from", ""), headers.get("date", ""), headers.get("subject", ""), text))
    return messages


def sample_photos(samples_dir: Path) -> list[SamplePhoto]:
    return [SamplePhoto(p.name, p.name.split(ASSET_SEPARATOR)[0], mimetypes.guess_type(p.name)[0] or "image/jpeg")
            for p in sorted((samples_dir / PHOTOS_DIR).glob("*")) if p.suffix.lower() in PHOTO_SUFFIXES]


def photo_path(samples_dir: Path, name: str) -> Path | None:
    """The sample photo's path, only if the name is a plain file in the photos folder."""
    path = (samples_dir / PHOTOS_DIR / name).resolve()
    folder = (samples_dir / PHOTOS_DIR).resolve()
    return path if path.parent == folder and path.is_file() and path.suffix.lower() in PHOTO_SUFFIXES else None
