"""Checks the repository's structural code rules: file length, function length, and the leading summary docstring.

It walks src/, tests/, and tools/ and reports every violation with its location, exiting non-zero when any exist.
It runs as part of `make lint` so the rules are enforced on every change, not remembered.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOTS = ("src", "tests", "tools")
MAX_FILE_LINES = 500
MAX_FUNCTION_LINES = 50
SUMMARY_PREFIXES = ('"""', "#")


def violations(path: Path) -> list[str]:
    """Return rule violations for one Python file."""
    source = path.read_text(encoding="utf-8")
    problems = []
    if source.count("\n") > MAX_FILE_LINES:
        problems.append(f"{path}: {source.count(chr(10))} lines (max {MAX_FILE_LINES})")
    if source.strip() and not source.lstrip().startswith(SUMMARY_PREFIXES):
        problems.append(f"{path}: missing leading summary docstring")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                problems.append(f"{path}:{node.lineno} {node.name} is {length} lines (max {MAX_FUNCTION_LINES})")
    return problems


def main() -> int:
    problems = [p for root in ROOTS for path in sorted(Path(root).rglob("*.py")) for p in violations(path)]
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
