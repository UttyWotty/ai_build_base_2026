"""Builds the chat messages for the language model from the catalog, calendar anchors, and one question.

The system message depends only on the catalog, the as-of date, and dimension values, so it is identical for every question and persona.
That keeps the model server's prompt cache warm; the persona, the question, and the binding hints go in the user message.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.term_matcher import TermMatches

ChatMessage = dict[str, str]
MAX_LISTED_VALUES = 50

RULES = """You translate business questions into a JSON decision for a governed supply chain metrics engine.
Reply with exactly one JSON object and nothing else. The three possible replies are:
{"action": "query", "spec": {"metrics": [...], "dimensions": [...], "filters": [...], "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}, "time_grain": "month"}}
{"action": "clarify", "question": "<one short question>", "options": ["<metric id>", ...]}
{"action": "unsupported", "reason": "<why no governed metric answers this>"}
Rules:
- Use only metric ids and dimension names listed below. Never invent metrics, dimensions, or columns.
- "dimensions" lists what to group by ("by X" in the question). Omit it or use [] when nothing is grouped.
- "filters" items look like {"dimension": "plant.plant_id", "operator": "equals" | "not_equals" | "in" | "not_in", "value": "US01" or [..]}; use listed values exactly.
- For relative periods copy the matching calendar anchor below exactly; omit "time_range" when no period is mentioned.
- "time_grain" is one of day, week, month, quarter, year; use it only when the question asks for a trend "by month", "per quarter", "over time".
- If the question uses a phrase that could mean several metrics and nothing in it settles which, reply with "clarify" and list the candidate metric ids.
- If the user message says metrics are bound by wording, use exactly those metrics."""


def build_system_message(catalog: SemanticCatalog, as_of: date, dimension_values: Mapping[str, Sequence[object]]) -> ChatMessage:
    """Static instructions plus the catalog (metrics, dimensions with values, calendar anchors)."""
    metric_lines = [
        f"- {m.id}: {m.label}. {m.description} Also called: {', '.join(m.synonyms) or '-'}."
        + (f" Not the same as: {', '.join(m.not_to_be_confused_with)}." if m.not_to_be_confused_with else "")
        for m in catalog.metrics.values()
    ]
    dimension_lines = []
    for name, definition in catalog.vocabulary.dimensions.items():
        values = list(dimension_values.get(name, ()))
        listed = f" Values: {', '.join(map(str, values))}." if 0 < len(values) <= MAX_LISTED_VALUES else ""
        dimension_lines.append(f"- {name} ({definition.label}; also: {', '.join(definition.synonyms) or '-'}).{listed}")
    anchor_lines = [f'- {name}: {{"start": "{r.start}", "end": "{r.end}"}}' for name, r in calendar_anchors(as_of).items()]
    content = "\n".join([
        RULES, "", f"Data is complete up to {as_of}.", "Calendar anchors:", *anchor_lines,
        "", "Metrics:", *metric_lines, "", "Dimensions:", *dimension_lines,
    ])
    return {"role": "system", "content": content}


def build_user_message(question: str, persona: str | None, catalog: SemanticCatalog, matches: TermMatches) -> ChatMessage:
    """The question with persona vocabulary and deterministic binding hints."""
    lines = []
    if persona is not None and persona in catalog.vocabulary.personas:
        definition = catalog.vocabulary.personas[persona]
        lines.append(f"Asked by the {definition.label} team ({definition.description})")
        if definition.dimension_vocabulary:
            lines.append("Team words for dimensions: " + json.dumps(dict(definition.dimension_vocabulary)))
    if matches.bound_metrics:
        lines.append(f"Metrics bound by wording (use exactly these): {', '.join(matches.bound_metrics)}")
    for match in matches.ambiguous:
        lines.append(f"The phrase '{match.term}' could mean: {', '.join(match.metrics)}. Choose one only if the question settles it; otherwise clarify.")
    lines.append(f"Question: {question}")
    return {"role": "user", "content": "\n".join(lines)}


def build_retry_message(problems: Sequence[str]) -> ChatMessage:
    """Feedback after an invalid reply."""
    listing = "\n".join(f"- {p}" for p in problems)
    return {"role": "user", "content": f"That reply was not valid:\n{listing}\nReply again with one corrected JSON object."}
