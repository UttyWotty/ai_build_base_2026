"""The record type that renderers produce and the writer persists: a relative path, a frame, and a file format.

Renderers stay pure by returning SourceFile values instead of writing files themselves.
The file format decides how the writer serializes the frame (Parquet for volume, xlsx for small exports).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class FileFormat(str, Enum):
    """Serialization format of a source file."""

    PARQUET = "parquet"
    XLSX = "xlsx"


@dataclass(frozen=True)
class SourceFile:
    """One file of a simulated source system."""

    relative_path: str
    frame: pd.DataFrame
    file_format: FileFormat
