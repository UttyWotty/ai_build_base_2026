"""Command line that evaluates the natural-language layer against a live model and writes a JSON report.

Model endpoint and name default to services.settings and can be overridden per run to compare models.
The report lands in data/eval/<model>.json; the console shows each case and the overall accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from supply_ontology.core.eval_cases import parse_cases
from supply_ontology.data_pipeline.llm_client import OpenAICompatibleClient
from supply_ontology.data_pipeline.semantic_files import (
    load_catalog,
    load_yaml_document,
)
from supply_ontology.services.evaluation import run_cases
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.settings import (
    DATA_DIR,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
    SEMANTIC_DIR,
)

CASES_FILE = Path("evaluation/supply/questions.yaml")
REPORT_DIRNAME = "eval"
SLUG_REPLACEMENTS = str.maketrans({"/": "__", ":": "_"})


def main(argv: list[str] | None = None) -> int:
    """Run the evaluation; exit code 0 regardless of accuracy (the report is the result)."""
    parser = argparse.ArgumentParser(description="Evaluate the natural-language layer against a live model.")
    parser.add_argument("--base-url", default=LLM_BASE_URL)
    parser.add_argument("--model", default=LLM_MODEL)
    parser.add_argument("--cases", type=Path, default=CASES_FILE)
    args = parser.parse_args(argv)
    catalog = load_catalog(SEMANTIC_DIR)
    service = NLService(catalog, QueryService(catalog), OpenAICompatibleClient(args.base_url, args.model, LLM_TIMEOUT_SECONDS))
    results = run_cases(service, parse_cases(load_yaml_document(args.cases)))
    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        print(f"{mark} [{result.seconds:5.1f}s x{result.model_calls}] {result.case.persona:11s} {result.case.question}")
        for problem in result.problems:
            print(f"       {problem}")
        if result.detail:
            print(f"       ({result.detail[:160]})")
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} passed with {args.model}")
    report = {
        "model": args.model, "as_of": str(service.query_service.as_of), "passed": passed, "total": len(results),
        "cases": [{"persona": r.case.persona, "question": r.case.question, "expect": r.case.expect,
                   "action": r.outcome.action, "metrics": list(r.outcome.metrics), "detail": r.detail, "passed": r.passed,
                   "problems": list(r.problems), "seconds": round(r.seconds, 2), "model_calls": r.model_calls}
                  for r in results],
    }
    path = DATA_DIR / REPORT_DIRNAME / f"{args.model.translate(SLUG_REPLACEMENTS)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
