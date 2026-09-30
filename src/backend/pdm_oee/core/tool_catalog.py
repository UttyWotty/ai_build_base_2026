"""The governed investigation tools: what each tool does, its parameters, and the rule that validates a call.

Parameters are dates, integers in a range, or choices from a named vocabulary (asset ids, sensors, losses...) supplied
at run time from the catalog and the data. A scope id is checked against the vocabulary its scope type names.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum


class ParamKind(str, Enum):
    DATE = "date"
    CHOICE = "choice"
    SCOPE_ID = "scope_id"
    INTEGER = "integer"


@dataclass(frozen=True)
class ParamSpec:
    name: str
    kind: ParamKind
    description: str
    vocabulary: str | None = None
    required: bool = True
    minimum: int = 1
    maximum: int = 20


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: tuple[ParamSpec, ...]


SCOPE_TYPE = ParamSpec("scope_type", ParamKind.CHOICE, "plant, site, line, or asset", "scope_type")
SCOPE_ID = ParamSpec("scope_id", ParamKind.SCOPE_ID, "id of the scope ('plant' for the whole plant)")
START = ParamSpec("start", ParamKind.DATE, "first day, YYYY-MM-DD")
END = ParamSpec("end", ParamKind.DATE, "day after the last day, YYYY-MM-DD")
ASSET = ParamSpec("asset_id", ParamKind.CHOICE, "asset id", "asset")
TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("oee_summary", "Availability, performance, quality, and OEE for a scope and period.", (SCOPE_TYPE, SCOPE_ID, START, END)),
    ToolSpec("oee_trend", "OEE and its factors per day, week, or month for a scope.",
             (SCOPE_TYPE, SCOPE_ID, START, END, ParamSpec("grain", ParamKind.CHOICE, "day, week, or month", "grain"))),
    ToolSpec("loss_breakdown", "Hours lost to each OEE loss for a scope and period, from planned time down to valuable time.",
             (SCOPE_TYPE, SCOPE_ID, START, END)),
    ToolSpec("top_loss_contributors", "The assets or lines that lost the most hours to one loss in a period.",
             (ParamSpec("loss", ParamKind.CHOICE, "loss id", "loss"), ParamSpec("group", ParamKind.CHOICE, "asset or line", "group"),
              START, END, ParamSpec("limit", ParamKind.INTEGER, "how many to list", required=False))),
    ToolSpec("sensor_trend", "Daily mean of a sensor's running readings on an asset, with its healthy range.",
             (ASSET, ParamSpec("sensor", ParamKind.CHOICE, "sensor position", "sensor"), START, END)),
    ToolSpec("failures", "Functional failures of an asset (or all assets of a line) with failure mode and downtime hours.",
             (SCOPE_TYPE, SCOPE_ID, START, END)),
    ToolSpec("work_order_history", "CMMS work orders of an asset: type, failure mode, dates, and description.", (ASSET, START, END)),
    ToolSpec("alerts", "Predictive alerts raised for an asset or line in a period, with outcome and priority.",
             (SCOPE_TYPE, SCOPE_ID, START, END)),
    ToolSpec("quality_drivers", "Weekly quality of a line's assets next to the weekly mean of each temperature sensor, with correlations.",
             (ParamSpec("line_id", ParamKind.CHOICE, "line id", "line"), START, END)),
)
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def validate_call(tool_name: str, arguments: Mapping[str, object], vocabularies: Mapping[str, Sequence[str]]) -> tuple[dict, list[str]]:
    """Clean arguments and the problems that stop the call; problems are phrased for the model to fix."""
    spec = TOOLS_BY_NAME.get(tool_name)
    if spec is None:
        return {}, [f"Unknown tool '{tool_name}'. Tools: {', '.join(TOOLS_BY_NAME)}"]
    problems = [f"Unknown argument '{a}' for {tool_name}" for a in arguments if a not in {p.name for p in spec.params}]
    clean: dict[str, object] = {}
    for param in spec.params:
        if param.name not in arguments:
            if param.required:
                problems.append(f"Missing argument '{param.name}' ({param.description}); put arguments inside \"arguments\": {{...}}")
            continue
        value, problem = _check(param, arguments[param.name], arguments, vocabularies)
        clean[param.name] = value
        problems += [problem] if problem else []
    if isinstance(clean.get("start"), date) and isinstance(clean.get("end"), date) and clean["end"] <= clean["start"]:
        problems.append("'end' must be after 'start'")
    return clean, problems


def _check(param: ParamSpec, value: object, arguments: Mapping[str, object], vocabularies: Mapping[str, Sequence[str]]) -> tuple[object, str | None]:
    if param.kind is ParamKind.DATE:
        try:
            return date.fromisoformat(str(value)), None
        except ValueError:
            return None, f"'{param.name}' must be a date YYYY-MM-DD, not {value!r}"
    if param.kind is ParamKind.INTEGER:
        if isinstance(value, bool) or not isinstance(value, int) or not param.minimum <= value <= param.maximum:
            return None, f"'{param.name}' must be an integer from {param.minimum} to {param.maximum}"
        return value, None
    vocabulary = str(arguments.get("scope_type")) if param.kind is ParamKind.SCOPE_ID else param.vocabulary
    allowed = vocabularies.get(vocabulary or "", ())
    if str(value) not in allowed:
        shown = ", ".join(list(allowed)[:12])
        return None, f"'{param.name}' {value!r} is not a known {vocabulary}; choose from: {shown}"
    return str(value), None
