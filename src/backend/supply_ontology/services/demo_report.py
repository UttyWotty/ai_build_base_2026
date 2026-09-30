"""Converts a consistency demo report to a JSON-ready dictionary.

The CLI saves the dictionary after a live run, and the UI can show a saved run without calling the model again.
Result frames are stored as lists of records with dates and other values written as text.
"""
from __future__ import annotations

import json
from dataclasses import asdict, fields

from supply_ontology.services.demo_models import DemoReport, NaiveRun, RecipeComparison

REPORT_VERSION = 1
FRAME_FIELD = "frame"


def report_to_dict(report: DemoReport, model: str) -> dict[str, object]:
    """Everything a reader needs to audit the run, plus the three verdicts."""
    return {
        "version": REPORT_VERSION,
        "model": model,
        "as_of": report.as_of.isoformat(),
        "verdicts": {
            "naive_agree": report.naive_agree,
            "naive_spread": report.naive_spread,
            "governed_consistent": report.governed_consistent,
            "governed_fingerprints": list(report.governed_fingerprints),
            "boundary_distinct": report.boundary_distinct,
        },
        "naive": [_naive_to_dict(run) for run in report.naive],
        "governed": [asdict(run) for run in report.governed],
        "boundary": asdict(report.boundary),
        "recipes": None if report.recipes is None else recipes_to_dict(report.recipes),
    }


def recipes_to_dict(comparison: RecipeComparison) -> dict[str, object]:
    """The team recipes and the governed reference for one period."""
    return {
        "period": {"start": comparison.period.start.isoformat(), "end": comparison.period.end.isoformat()},
        "recipes_agree": comparison.recipes_agree,
        "recipes_spread": comparison.recipes_spread,
        "governed": {"metric": comparison.governed_metric, "value": comparison.governed_value,
                     "fingerprint": comparison.governed_fingerprint},
        "runs": [{**asdict(run.recipe), "choices": list(run.recipe.choices), "value": run.value, "error": run.error}
                 for run in comparison.runs],
    }


def _naive_to_dict(run: NaiveRun) -> dict[str, object]:
    values = {f.name: getattr(run, f.name) for f in fields(run) if f.name != FRAME_FIELD}
    rows = None if run.frame is None else json.loads(run.frame.to_json(orient="records", date_format="iso"))
    return {**values, "rows": rows}

