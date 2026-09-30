"""Filesystem adapter for the fitted predictor: the classifier, its threshold, its feature list, and the backtest report.

The classifier is pickled next to a JSON file with everything a reader needs to use or audit it.
Only files written by this project are ever loaded, since unpickling runs code.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

MODEL_FILENAME = "failure_model.pkl"
REPORT_FILENAME = "failure_model.json"
JSON_INDENT = 2
FILE_ENCODING = "utf-8"


def save_model(model: object, report: dict[str, object], model_dir: Path) -> Path:
    """Write the model and its report; return the report path."""
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / MODEL_FILENAME).write_bytes(pickle.dumps(model))
    path = model_dir / REPORT_FILENAME
    path.write_text(json.dumps(report, indent=JSON_INDENT, default=str) + "\n", encoding=FILE_ENCODING)
    return path


def load_model(model_dir: Path) -> tuple[object, dict[str, object]]:
    """The saved model and its report."""
    model = pickle.loads((model_dir / MODEL_FILENAME).read_bytes())
    report = json.loads((model_dir / REPORT_FILENAME).read_text(encoding=FILE_ENCODING))
    return model, report
