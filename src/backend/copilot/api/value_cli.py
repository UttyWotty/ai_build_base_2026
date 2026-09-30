"""Command line that prints the copilot's track record: every alert's plan scored against what really happened.

It prints the totals, the alerts where the copilot's plan differed from the site's own choice, and the method.
No model is called; the recommendations come from the governed impact rules.
"""
from __future__ import annotations

from copilot.core.value_views import track_record_result
from copilot.services.factory import default_impact_service
from copilot.services.value_service import ValueService


def main() -> int:
    result = track_record_result(*ValueService(default_impact_service()).track_record())
    s = result["summary"]
    print(f"{s['alerts']} alerts from {s['period']['first']} to {s['period']['last']}: {s['real_failures']} real failures, "
          f"{s['false_alerts']} false alerts; the plan differed from the site's own choice {s['plans_that_differ']} times")
    print(f"Saved {s['hours_saved']} h and ${s['usd_saved_on_failures']:,} on real failures; spent "
          f"${s['usd_spent_on_false_alerts']:,} on false alerts; net ${s['net_usd']:,}")
    for case in result["cases"]:
        if case["recommended_kind"] != case["baseline_kind"]:
            outcome = f"failed {case['failed_at']}" if case["failed_at"] else "no failure"
            print(f"  {case['alert_id']:26s} {case['recommended_kind']:13s} vs {case['baseline_kind']:10s} "
                  f"{outcome:24s} saved {case['hours_saved']:6.1f} h ${case['usd_saved']:>9,}")
    for line in result["method"]:
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
