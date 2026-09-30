"""Command line for the investigation layer: ask one question, or run the evaluation set, against a live model.

`ask` prints the answer, whether its numbers were verified, and the tools it used. `eval` runs evaluation/investigation.yaml
and writes a report per model to data/eval/. Both use the configured model unless --provider, --model, or --base-url say otherwise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_gateway import ModelSelection, build_llm_client
from llm_gateway.cli_args import add_model_arguments, selection_from_args
from pdm_oee.core.investigation_eval import InvestigationOutcome, parse_cases, score
from pdm_oee.data_pipeline.replay_store import read_replay_alerts
from pdm_oee.data_pipeline.semantic_files import load_catalog, load_yaml_document
from pdm_oee.services.investigation_service import InvestigationService
from pdm_oee.services.investigation_tools import ToolBox
from pdm_oee.services.oee_service import OEEService
from pdm_oee.services.settings import (
    DATA_DIR,
    REPLAY_PATH,
    SEMANTIC_DIR,
)

CASES_FILE = Path("evaluation/pdm/investigation.yaml")
REPORT_DIR = DATA_DIR / "eval"
SLUG = str.maketrans({"/": "__", ":": "_"})
JSON_INDENT = 2


def build_service(selection: ModelSelection) -> InvestigationService:
    catalog = load_catalog(SEMANTIC_DIR)
    toolbox = ToolBox(catalog, OEEService(catalog), read_replay_alerts(REPLAY_PATH))
    return InvestigationService(toolbox, build_llm_client(selection))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the investigation layer, or evaluate it, against a live model.")
    parser.add_argument("command", choices=("ask", "eval"))
    parser.add_argument("question", nargs="?", default="")
    add_model_arguments(parser)
    args = parser.parse_args(argv)
    selection = selection_from_args(args)
    service = build_service(selection)
    if args.command == "ask":
        result = service.ask(args.question)
        print(result.answer or f"No answer ({result.status})")
        print(f"\nverified: {result.verified}; tools: {', '.join(result.tools_used) or 'none'}")
        return 0
    rows = []
    for case in parse_cases(load_yaml_document(CASES_FILE)):
        result = service.ask(case.question)
        problems = score(case, InvestigationOutcome(result.tools_used, result.answer, result.verified))
        rows.append({"question": case.question, "passed": not problems, "problems": problems, "answer": result.answer,
                     "tools": list(result.tools_used), "status": result.status})
        print(f"{'PASS' if not problems else 'FAIL'} {case.question}" + "".join(f"\n       {p}" for p in problems))
    passed = sum(r["passed"] for r in rows)
    print(f"\n{passed}/{len(rows)} passed with {selection.label}")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"investigation_{selection.label.translate(SLUG)}.json").write_text(
        json.dumps({"model": selection.label, "provider": selection.provider.value, "passed": passed, "total": len(rows), "cases": rows}, indent=JSON_INDENT) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
