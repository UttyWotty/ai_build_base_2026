"""Command line that runs the consistency demo against a live model and saves the run as JSON.

It prints the team recipes, naive text-to-SQL, the governed layer, and the supplier boundary; --offline prints only the
first part, which needs no model.
The saved run lands in data/demo/<model>.json so the UI can replay it without calling the model.
"""
from __future__ import annotations

import argparse
import json

from supply_ontology.data_pipeline.llm_client import OpenAICompatibleClient
from supply_ontology.data_pipeline.semantic_files import (
    load_catalog,
)
from supply_ontology.services.consistency_demo import ConsistencyDemo
from supply_ontology.services.demo_models import (
    DemoReport,
    GovernedRun,
    RecipeComparison,
)
from supply_ontology.services.demo_report import report_to_dict
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.query_service import QueryService
from supply_ontology.services.recipe_comparison import compare_recipes
from supply_ontology.services.service_factory import (
    default_raw_database,
    load_team_recipes,
)
from supply_ontology.services.settings import (
    DEMO_DIR,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
    SEMANTIC_DIR,
)

SLUG_REPLACEMENTS = str.maketrans({"/": "__", ":": "_"})
FINGERPRINT_SHOWN_CHARS = 12
PERCENT = 100


def main(argv: list[str] | None = None) -> int:
    """Run the demo once and save it."""
    parser = argparse.ArgumentParser(description="Run the consistency demo against a live model.")
    parser.add_argument("--base-url", default=LLM_BASE_URL)
    parser.add_argument("--model", default=LLM_MODEL)
    parser.add_argument("--offline", action="store_true", help="only the team recipes and the governed answer; no model")
    args = parser.parse_args(argv)
    catalog = load_catalog(SEMANTIC_DIR)
    query_service, raw_database = QueryService(catalog), default_raw_database()
    recipes = load_team_recipes(catalog)
    if args.offline:
        print_recipes(compare_recipes(recipes, raw_database, query_service))
        return 0
    client = OpenAICompatibleClient(args.base_url, args.model, LLM_TIMEOUT_SECONDS)
    report = ConsistencyDemo(NLService(catalog, query_service, client), raw_database, recipes=recipes).run()
    print_report(report)
    path = DEMO_DIR / f"{args.model.translate(SLUG_REPLACEMENTS)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_to_dict(report, args.model), indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nSaved: {path}")
    return 0


def print_recipes(comparison: RecipeComparison) -> None:
    """Each team's own recipe next to the governed answer for the same period."""
    print(f"The problem, reproduced: each team's own recipe for customer OTD, {comparison.period.start} to {comparison.period.end}")
    for run in comparison.runs:
        closest = f"  (effectively {run.recipe.closest_metric})" if run.recipe.closest_metric else ""
        print(f"   {run.recipe.persona:11s} {run.error or _percent(run.value):>8s}  {run.recipe.label}{closest}")
    spread = "" if comparison.recipes_spread is None else f" (spread {comparison.recipes_spread * PERCENT:.1f} points)"
    print(f"   Recipes agree: {'yes' if comparison.recipes_agree else 'no'}{spread}")
    print(f"   Governed {comparison.governed_metric}: {_percent(comparison.governed_value)}"
          f"  sql {comparison.governed_fingerprint[:FINGERPRINT_SHOWN_CHARS]}")


def print_report(report: DemoReport) -> None:
    """The recipes, the problem, the fix, and the boundary, in plain text."""
    print(f"Data as of {report.as_of}\n")
    if report.recipes is not None:
        print_recipes(report.recipes)
    print("\n1. The problem: naive text-to-SQL on the raw sources")
    for run in report.naive:
        outcome = run.error or (run.sql or "").splitlines()[0]
        print(f"   {run.persona:11s} {_percent(run.value):>8s}  x{run.attempts}  {outcome[:90]}")
    spread = "" if report.naive_spread is None else f" (spread {report.naive_spread * PERCENT:.1f} points)"
    print(f"   Answers agree: {'yes' if report.naive_agree else 'no'}{spread}")
    print("\n2. The fix: the same phrasings through the governed layer")
    for run in report.governed:
        print(f"   {_governed_line(run)}")
    print(f"   One SQL fingerprint and one answer: {'yes' if report.governed_consistent else 'no'}")
    print(f"\n3. The boundary: \"{report.boundary.question}\"\n   {_governed_line(report.boundary)}")
    print(f"   Resolved to its own metric: {'yes' if report.boundary_distinct else 'no'}")


def _governed_line(run: GovernedRun) -> str:
    if run.fingerprint is None:
        return f"{run.persona:11s} {run.outcome}: {run.detail}"
    metrics = ", ".join(run.metrics)
    return f"{run.persona:11s} {_percent(run.value):>8s}  {metrics}  sql {run.fingerprint[:FINGERPRINT_SHOWN_CHARS]}  ({run.resolved_by})"


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value * PERCENT:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
