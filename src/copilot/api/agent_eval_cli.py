"""Command line that runs the copilot evaluation scenarios against a live model and writes a JSON report.

Proposals made during the evaluation go to a separate file, so the approval queue of the app stays clean.
The report lands in data/copilot/eval/<model>.json; the console shows each case and the pass count.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from copilot.core.agent_eval import RunOutcome, parse_cases, score
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.services.agent_runner import run_copilot
from copilot.services.factory import default_services
from copilot.services.settings import PROPOSALS_PATH
from llm_gateway.cli_args import add_model_arguments, selection_from_args
from pdm_oee.data_pipeline.semantic_files import load_yaml_document

CASES_FILE = Path("evaluation/copilot/scenarios.yaml")
REPORT_DIR = PROPOSALS_PATH.parent / "eval"
SLUG = str.maketrans({"/": "__", ":": "_"})
JSON_INDENT = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the operations copilot against a live model.")
    parser.add_argument("--only", nargs="*", default=None, help="case ids to run (default: all)")
    add_model_arguments(parser)
    args = parser.parse_args(argv)
    selection = selection_from_args(args)
    eval_store = ProposalStore(REPORT_DIR / "proposals.json")
    services = default_services()
    rows = []
    for case in parse_cases(load_yaml_document(CASES_FILE)):
        if args.only and case.case_id not in args.only:
            continue
        tools = services.tools_at(case.as_of)
        tools.proposals = eval_store
        run = run_copilot(case.question, tools, selection)
        calls = tuple((s.name, dict(s.payload)) for s in run.steps if s.kind == "tool_call")
        problems = score(case, RunOutcome(calls, run.answer, run.unexplained_numbers))
        rows.append({"id": case.case_id, "passed": not problems, "problems": problems, "seconds": run.seconds,
                     "tools": list(run.tools_used), "answer": run.answer})
        print(f"{'PASS' if not problems else 'FAIL'} {case.case_id:18s} {run.seconds:6.1f}s  {', '.join(problems)}")
    passed = sum(r["passed"] for r in rows)
    print(f"\n{passed}/{len(rows)} passed with {selection.label}")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{selection.label.translate(SLUG)}.json"
    path.write_text(json.dumps({"model": selection.label, "provider": selection.provider.value, "passed": passed,
                                "total": len(rows), "cases": rows}, indent=JSON_INDENT) + "\n", encoding="utf-8")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
