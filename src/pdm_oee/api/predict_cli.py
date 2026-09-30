"""Command line that runs the failure prediction backtest, prints both predictors' results, and saves the model.

The model, its threshold, its features, and the report land in data/models/ for the alert service to replay.
Results are event-level: failures caught with at least a day's lead, false alerts per asset-month, and median lead.
"""
from __future__ import annotations

from dataclasses import asdict

from pdm_oee.data_pipeline.model_store import save_model
from pdm_oee.data_pipeline.semantic_files import load_catalog
from pdm_oee.services.prediction_service import PredictionService
from pdm_oee.services.settings import MODEL_DIR, SEMANTIC_DIR

PERCENT = 100


def main() -> int:
    service = PredictionService(load_catalog(SEMANTIC_DIR))
    backtest = service.backtest()
    hours = backtest.panel["hour"]
    spans = {name: f"{hours[rows].min():%Y-%m-%d} to {hours[rows].max():%Y-%m-%d}" for name, rows in backtest.blocks.items()}
    print(f"Fit {spans['fit']}, threshold {spans['validation']}, test {spans['test']}\n")
    print(f"{'predictor':10s} {'caught':>9s} {'recall':>7s} {'false/asset-month':>18s} {'late':>5s} {'median lead h':>14s}")
    for name, result in backtest.test.items():
        lead = "-" if result.median_lead_hours is None else f"{result.median_lead_hours:.0f}"
        print(f"{name:10s} {result.caught_failures:>4d} / {result.evaluable_failures:<2d} {result.recall * PERCENT:>6.1f}% "
              f"{result.false_alerts_per_asset_month:>18.2f} {result.late_alerts:>5d} {lead:>14s}")
    report = {"settings": asdict(service.settings), "features": backtest.features, "blocks": spans,
              "threshold": backtest.validation["model"].threshold,
              "validation": {k: asdict(v) for k, v in backtest.validation.items()},
              "test": {k: asdict(v) for k, v in backtest.test.items()}}
    path = save_model(backtest.model, report, MODEL_DIR)
    print(f"\nSaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
