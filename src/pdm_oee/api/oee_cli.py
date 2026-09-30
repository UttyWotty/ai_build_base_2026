"""Command line that prints OEE and its factors by a grouping, and the loss waterfall, for a period.

The period defaults to the last four complete ISO weeks of data; groupings are those OEEService supports.
Values are printed as percentages; the waterfall in hours.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

import pandas as pd

from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.services.oee_service import GROUPINGS, OEEService
from pdm_oee.services.settings import SEMANTIC_DIR

DEFAULT_WEEKS = 4
REPORT_METRICS = ("availability", "performance", "quality", "oee")
PERCENT = 100
MINUTES_PER_HOUR = 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print OEE by a grouping and the loss waterfall.")
    parser.add_argument("--by", choices=GROUPINGS, default="line_id")
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)
    service = OEEService(load_catalog(SEMANTIC_DIR))
    last = pd.to_datetime(service.measures["shift_date"]).max().date()
    end = args.end or last - timedelta(days=last.weekday())
    start = args.start or end - timedelta(weeks=DEFAULT_WEEKS)
    table = service.metrics(REPORT_METRICS, [args.by], start, end)
    for metric in REPORT_METRICS:
        table[metric] = (table[metric] * PERCENT).round(1)
    print(f"OEE by {args.by}, {start} to {end} (percent)\n{table.to_string(index=False)}\n")
    steps = service.loss_waterfall(start, end)
    steps["hours"] = (steps.pop("minutes") / MINUTES_PER_HOUR).round(0)
    print(f"Loss waterfall (hours)\n{steps.to_string(index=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
