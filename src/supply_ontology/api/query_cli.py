"""Command line for running a governed query spec given as JSON, printing the SQL fingerprint, SQL, and result.

It is the simplest way to see the compiler work: `query-metric '{"metrics": ["otd"], "time_grain": "quarter"}'`.
Paths come from services.settings; the conformed layer must exist (run `make conform`).
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from supply_ontology.core.query_spec_parser import parse_query_spec
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.settings import SEMANTIC_DIR

DISPLAY_ROWS = 50
DISPLAY_WIDTH = 160


def main(argv: list[str] | None = None) -> int:
    """Run one spec and print the answer with its provenance."""
    parser = argparse.ArgumentParser(description="Run a governed metric query spec.")
    parser.add_argument("spec", help="query spec as JSON")
    parser.add_argument("--show-sql", action="store_true", help="print the compiled SQL")
    args = parser.parse_args(argv)
    service = QueryService(load_catalog(SEMANTIC_DIR))
    result = service.run(parse_query_spec(json.loads(args.spec)))
    print(f"as of {result.as_of}  fingerprint {result.compiled.fingerprint}")
    for metric in result.metrics:
        print(f"- {metric.id}: {metric.description}")
    if args.show_sql:
        print(result.compiled.sql)
        print("parameters:", list(result.compiled.parameters))
    with pd.option_context("display.max_rows", DISPLAY_ROWS, "display.width", DISPLAY_WIDTH):
        print(result.frame)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
