"""Shapes the value backtest into JSON-ready results for the API and the command line.

Money is rounded to whole dollars and hours to one decimal, the way the interface shows them.
Each case keeps both prices, so a reader can check the saving line by line.
"""
from __future__ import annotations

from copilot.core.value_backtest import CaseValue, RealisedCost, ValueSummary

TIME_FORMAT = "%Y-%m-%d %H:%M"


def _cost(cost: RealisedCost) -> dict[str, float]:
    return {"extra_cost_usd": round(cost.extra_cost_usd), "lost_hours": cost.lost_hours,
            "lost_contribution_usd": round(cost.lost_contribution_usd), "total_usd": round(cost.total_usd)}


def case_row(case: CaseValue) -> dict[str, object]:
    return {"alert_id": case.alert_id, "asset_id": case.asset_id, "site_id": case.site_id,
            "raised_at": case.raised_at.strftime(TIME_FORMAT),
            "failed_at": case.failed_at.strftime(TIME_FORMAT) if case.failed_at else None,
            "recommended_kind": case.recommended_kind, "baseline_kind": case.baseline_kind,
            "copilot": _cost(case.copilot), "baseline": _cost(case.baseline),
            "hours_saved": case.hours_saved, "usd_saved": round(case.usd_saved)}


def track_record_result(cases: list[CaseValue], summary: ValueSummary) -> dict[str, object]:
    return {
        "summary": {"alerts": summary.alerts, "real_failures": summary.real_failures, "false_alerts": summary.false_alerts,
                    "plans_that_differ": summary.plans_that_differ, "hours_saved": summary.hours_saved,
                    "usd_saved_on_failures": round(summary.usd_saved_on_failures),
                    "usd_spent_on_false_alerts": round(summary.usd_spent_on_false_alerts),
                    "net_usd": round(summary.net_usd), "by_site": {k: round(v) for k, v in summary.by_site.items()},
                    "period": {"first": cases[0].raised_at.strftime(TIME_FORMAT) if cases else None,
                               "last": cases[-1].raised_at.strftime(TIME_FORMAT) if cases else None}},
        "cases": [case_row(c) for c in cases],
        "method": [
            "Every alert that opened a draft work order is analysed at the moment it was raised, as the copilot would have.",
            "The recommended option and the site's own option (stock, then open order, then a new order) are priced at "
            "the real outcome: a spare in hand before the failure means a planned repair, a later one adds the wait.",
            "False alerts cost only the recommended option's extra spend, and that spend is subtracted from the value.",
            "Alerts are scored independently; a transfer is not charged for the sister site's later needs.",
        ],
    }
