"""Command line that prints the impact analysis for one alert: spares, supplier record, options, and customers at risk.

The analysis time defaults to when the alert was raised; --as-of moves it later to replay how the picture changed.
`--list START END` prints the alerts raised in a window instead.
"""
from __future__ import annotations

import argparse
from datetime import datetime

from copilot.core.impact_model import ImpactReport
from copilot.services.factory import default_alert_book, default_impact_service

MAX_ORDERS_SHOWN = 8


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Impact analysis for a failure alert.")
    parser.add_argument("alert_id", nargs="?", default="")
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=None)
    parser.add_argument("--list", nargs=2, type=datetime.fromisoformat, metavar=("START", "END"))
    args = parser.parse_args(argv)
    if args.list:
        for alert in default_alert_book().raised_between(*args.list):
            print(f"{alert.alert_id:28s} {alert.raised_at:%Y-%m-%d %H:%M} {alert.failure_mode:24s} {alert.priority}")
        return 0
    print_report(default_impact_service().analyse(args.alert_id, args.as_of))
    return 0


def print_report(report: ImpactReport) -> None:
    a = report.alert
    print(f"{a.alert_id}: {a.failure_mode} on {a.asset_id} ({report.asset.line_id}), as of {report.as_of:%Y-%m-%d %H:%M}")
    print(f"  repair deadline {a.deadline_at:%Y-%m-%d %H:%M}, repair {a.repair_hours:g} h, planned slot: {a.planned_slot}")
    if report.spare is not None and report.local is not None:
        print(f"  spare {report.spare.spare_part_id} {report.spare.label}: {report.local.on_hand} on hand at {report.local.site_id}, "
              f"open orders {[o.po_id for o in report.local.open_orders]}, queue {[c.alert_id for c in report.local.claims]}")
        for sister in report.sisters:
            print(f"  sister {sister.site_id}: {sister.on_hand} on hand, queue {[c.alert_id for c in sister.claims]}")
    if report.supplier is not None:
        s = report.supplier
        share = "n/a" if s.on_time_share is None else f"{s.on_time_share:.1%}"
        print(f"  supplier {s.supplier_id} {s.supplier_name}: on time {share}, expected {s.expected_days_late:g} days late "
              f"({s.window_start} to {s.window_end}, sql {s.sql_fingerprint})")
    lead = report.lead
    if lead.count:
        print(f"  past {lead.failure_mode} alerts: {lead.count}, fastest failure {lead.fastest_hours:g} h, median {lead.median_hours:g} h")
    print(f"  line rate {report.economics.units_per_hour:.1f} units/h at {report.economics.contribution_usd_per_unit:g} USD/unit")
    for option in report.options:
        mark = "*" if option == report.recommended else " "
        print(f" {mark} {option.kind.value:15s} {option.source:14s} ready {option.ready_at:%m-%d %H:%M}  extra {option.extra_cost_usd:>8,.0f}"
              f"  down {option.downtime_hours:>5.1f} h  lost {option.lost_contribution_usd:>9,.0f}  total {option.total_cost_usd:>9,.0f}"
              f"  orders at risk {len(option.orders_at_risk)}  worst case down {option.worst_case_downtime_hours} h")
    for order in report.recommended.orders_at_risk[:MAX_ORDERS_SHOWN]:
        print(f"      {order.so_line_id} {order.customer_name[:28]:28s} {order.part_id} x{order.quantity} due {order.committed_date}")


if __name__ == "__main__":
    raise SystemExit(main())
