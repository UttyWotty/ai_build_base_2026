"""Content fingerprints for data frames, independent of the file format they are stored in.

A fingerprint covers column names, dtypes, and every value in row order, so equal fingerprints mean identical content.
The manifest records one per file, which makes determinism checkable without comparing xlsx bytes.
"""
from __future__ import annotations

import hashlib

import pandas as pd

HEADER_SEPARATOR = "|"


def frame_fingerprint(frame: pd.DataFrame) -> str:
    """SHA-256 over the header and the row-wise hash of every value."""
    digest = hashlib.sha256()
    header = HEADER_SEPARATOR.join(f"{name}:{dtype}" for name, dtype in frame.dtypes.items())
    digest.update(header.encode())
    digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return digest.hexdigest()
