"""Parses the copilot evaluation scenarios and scores one agent run against its case.

A run passes when it called every required tool, its answer contains every required phrase, the number check found
nothing unexplained, and, for action requests, it proposed the expected option. Scoring is pure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pdm_oee.core.field_readers import (
    as_list,
    as_mapping,
    optional_mapping,
    optional_str_list,
    reject_unknown_keys,
    require_str,
)

CASE_KEYS = frozenset({"id", "as_of", "question", "tools", "answer_contains", "proposal"})
PROPOSAL_KEYS = frozenset({"alert_id", "option_kind", "option_source"})
PROPOSAL_TOOL = "propose_action_plan"


@dataclass(frozen=True)
class ExpectedProposal:
    alert_id: str
    option_kind: str
    option_source: str


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    as_of: datetime
    question: str
    tools: tuple[str, ...]
    answer_contains: tuple[str, ...]
    proposal: ExpectedProposal | None


@dataclass(frozen=True)
class RunOutcome:
    """What the scorer needs from a run."""

    tool_calls: tuple[tuple[str, dict[str, object]], ...]
    answer: str
    unexplained_numbers: tuple[str, ...]


def parse_cases(raw: object) -> tuple[EvalCase, ...]:
    root = as_mapping(raw, "evaluation")
    cases = []
    for index, item in enumerate(as_list(root.get("cases"), "evaluation.cases")):
        path = f"evaluation.cases[{index}]"
        entry = as_mapping(item, path)
        reject_unknown_keys(entry, CASE_KEYS, path)
        proposal = optional_mapping(entry, "proposal", path)
        expected = None
        if proposal:
            reject_unknown_keys(proposal, PROPOSAL_KEYS, f"{path}.proposal")
            expected = ExpectedProposal(*(require_str(proposal, k, f"{path}.proposal")
                                          for k in ("alert_id", "option_kind", "option_source")))
        cases.append(EvalCase(require_str(entry, "id", path), datetime.fromisoformat(require_str(entry, "as_of", path)),
                              require_str(entry, "question", path), optional_str_list(entry, "tools", path),
                              optional_str_list(entry, "answer_contains", path), expected))
    return tuple(cases)


def score(case: EvalCase, outcome: RunOutcome) -> list[str]:
    """Problems with the run; empty means it passed."""
    called = [name for name, _ in outcome.tool_calls]
    problems = [f"did not call {tool}" for tool in case.tools if tool not in called]
    answer = outcome.answer.lower()
    problems += [f"answer lacks {phrase!r}" for phrase in case.answer_contains if phrase.lower() not in answer]
    if not outcome.answer:
        problems.append("no answer")
    if outcome.unexplained_numbers:
        problems.append(f"unexplained numbers: {', '.join(outcome.unexplained_numbers)}")
    if case.proposal is not None and not _proposed(case.proposal, outcome):
        problems.append(f"no proposal {case.proposal.option_kind}/{case.proposal.option_source} for {case.proposal.alert_id}")
    return problems


def _proposed(expected: ExpectedProposal, outcome: RunOutcome) -> bool:
    return any(name == PROPOSAL_TOOL and args.get("alert_id") == expected.alert_id
               and args.get("option_kind") == expected.option_kind and args.get("option_source") == expected.option_source
               for name, args in outcome.tool_calls)
