"""Command line that asks the operations copilot one question at the demo clock and prints its trace and answer.

The model follows the gateway settings unless --provider, --model, or --base-url say otherwise.
The answer is marked verified when every number in it appears in a tool result.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

from copilot.services.agent_runner import AgentRun, run_copilot
from copilot.services.factory import default_copilot_tools
from copilot.services.settings import DEMO_AS_OF
from llm_gateway.cli_args import add_model_arguments, selection_from_args

PAYLOAD_CHARS = 160


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the operations copilot.")
    parser.add_argument("question")
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.fromisoformat(DEMO_AS_OF))
    add_model_arguments(parser)
    args = parser.parse_args(argv)
    run = run_copilot(args.question, default_copilot_tools(args.as_of), selection_from_args(args))
    print_run(run)
    return 0


def print_run(run: AgentRun) -> None:
    print(f"as of {run.as_of:%Y-%m-%d %H:%M}, model {run.model}, {run.seconds:g} s")
    for step in run.steps:
        if step.kind != "text":
            text = json.dumps(step.payload, default=str)
            print(f"  {step.kind:11s} {step.name:22s} {text[:PAYLOAD_CHARS]}")
    print("\n" + (run.answer or "(no answer)"))
    status = "verified" if run.verified else f"unverified numbers: {', '.join(run.unexplained_numbers) or 'no answer'}"
    print(f"\n[{status}; tools: {', '.join(run.tools_used) or 'none'}]")


if __name__ == "__main__":
    raise SystemExit(main())
