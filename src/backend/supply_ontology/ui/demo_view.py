"""Shows the consistency demo: team recipes against the governed answer, then a saved live run of the three parts.

The recipe table is computed from the raw sources; saved runs come from `make demo`. This view never calls the model.
Each part ends with its verdict so the point of the demo is stated, not left to the reader.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import streamlit as st

from supply_ontology.core.enums import MetricFormat
from supply_ontology.services.demo_models import RecipeComparison
from supply_ontology.ui.presenters import format_value

FINGERPRINT_SHOWN_CHARS = 12
YES_NO = {True: "yes", False: "no"}


def render_recipe_comparison(comparison: RecipeComparison) -> None:
    """Each team's own recipe next to the governed answer for the same period."""
    st.subheader("The problem, reproduced: each team's own recipe")
    st.caption(f"Customer on-time delivery, {comparison.period.start} to {comparison.period.end}. No model involved.")
    rows = [{"Team": run.recipe.persona, "Recipe": run.recipe.label, "Answer": run.error or _percent(run.value),
             "Effectively computes": run.recipe.closest_metric or "no declared metric",
             "What differs from the governed definition": " ".join(run.recipe.choices)} for run in comparison.runs]
    rows.append({"Team": "governed", "Recipe": f"{comparison.governed_metric} from the catalog",
                 "Answer": _percent(comparison.governed_value), "Effectively computes": comparison.governed_metric,
                 "What differs from the governed definition": f"SQL fingerprint {comparison.governed_fingerprint[:FINGERPRINT_SHOWN_CHARS]}"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    spread = comparison.recipes_spread
    extra = "" if spread is None else f", spread {spread * 100:.1f} points"
    st.markdown(f"**Recipes agree:** {YES_NO[comparison.recipes_agree]}{extra}")


def render_saved_demo(runs: Mapping[str, Mapping[str, object]]) -> None:
    """Pick a saved run and show its three parts."""
    if not runs:
        st.info("No saved demo run yet. Run `make demo` while the local model is available, then reload.")
        return
    model = st.selectbox("Saved run", list(runs), index=len(runs) - 1)
    report = runs[model]
    verdicts = report["verdicts"]
    st.caption(f"Model {model}, data as of {report['as_of']}.")
    st.subheader("1. The problem: naive text-to-SQL on the raw sources")
    for run in report["naive"]:
        tries = run.get("attempts") or 1
        retried = "" if tries == 1 else f" (after {tries} attempts)"
        with st.expander(f"{run['persona']}: {_percent(run['value'])}{retried}  {run['question']}"):
            if run["sql"]:
                st.code(run["sql"], language="sql")
            if run["error"]:
                st.error(run["error"])
    spread = verdicts["naive_spread"]
    extra = "" if spread is None else f", spread {spread * 100:.1f} points"
    st.markdown(f"**Answers agree:** {YES_NO[bool(verdicts['naive_agree'])]}{extra}")
    st.subheader("2. The fix: the same phrasings through the governed layer")
    st.dataframe(pd.DataFrame([_governed_row(r) for r in report["governed"]]), hide_index=True, width="stretch")
    st.markdown(f"**One SQL fingerprint and one answer:** {YES_NO[bool(verdicts['governed_consistent'])]}")
    st.subheader("3. The boundary")
    st.dataframe(pd.DataFrame([_governed_row(report["boundary"])]), hide_index=True, width="stretch")
    st.markdown(f"**Resolved to its own metric:** {YES_NO[bool(verdicts['boundary_distinct'])]}")


def _governed_row(run: Mapping[str, object]) -> dict[str, object]:
    fingerprint = run.get("fingerprint") or ""
    return {"Persona": run["persona"], "Question": run["question"], "Metric": ", ".join(run["metrics"]),
            "Answer": _percent(run["value"]), "SQL fingerprint": str(fingerprint)[:FINGERPRINT_SHOWN_CHARS],
            "Resolved by": run.get("resolved_by") or run.get("outcome")}


def _percent(value: object) -> str:
    return format_value(value, MetricFormat.PERCENT)
