"""Builders for small, valid raw catalog documents that tests copy and break one field at a time.

Each builder returns a fresh nested dict, so tests can mutate it freely.
The documents are deliberately tiny: one asset class, a minimal loss taxonomy, and a handful of measures and metrics.
"""
from __future__ import annotations

from copy import deepcopy

RawDocument = dict[str, object]

_PLANT: RawDocument = {
    "sensor_types": {"vibration": {"label": "Vibration", "unit": "mm_per_s"},
                     "temperature": {"label": "Temperature", "unit": "deg_c"}},
    "asset_classes": {"pump_station": {
        "label": "Pump station",
        "components": {"bearing": {"label": "Bearing"}, "seal": {"label": "Seal"}},
        "sensors": {"bearing_vibration": {"label": "Vibration", "type": "vibration", "component": "bearing",
                                          "normal_range": [0.5, 3.0]},
                    "bearing_temperature": {"label": "Temperature", "type": "temperature", "component": "bearing",
                                            "normal_range": [20, 60]}},
        "failure_modes": {
            "bearing_wear": {"label": "Bearing wear", "component": "bearing",
                             "symptoms": ["bearing_vibration", "bearing_temperature"], "pf_interval_days": 6,
                             "repair_hours": 8, "recommended_action": "Replace the bearing."},
            "seal_rupture": {"label": "Seal rupture", "component": "seal", "repair_hours": 3,
                             "recommended_action": "Replace the seal."}}}},
}

_LOSSES: RawDocument = {
    "losses": {
        "breakdowns": {"label": "Breakdowns", "factor": "availability", "source": "stop_reason"},
        "small_stops": {"label": "Small stops", "factor": "performance", "source": "short_stop"},
        "reduced_speed": {"label": "Reduced speed", "factor": "performance", "source": "speed_gap"},
        "startup_rejects": {"label": "Startup rejects", "factor": "quality", "source": "startup_scrap"},
        "production_rejects": {"label": "Production rejects", "factor": "quality", "source": "production_scrap"},
    },
    "planned_stop_reasons": {"scheduled_break": {"label": "Break"}},
    "loss_reasons": {"equipment_failure": {"label": "Failure", "loss": "breakdowns"}},
}

_MEASURES: RawDocument = {"measures": {
    "planned_production_time": {"label": "Planned", "grain": "asset_shift", "unit": "minutes", "definition": "d"},
    "run_time": {"label": "Run", "grain": "asset_shift", "unit": "minutes", "definition": "d",
                 "parameters": {"small_stop_threshold_minutes": 5}},
    "total_count": {"label": "Total", "grain": "asset_shift", "unit": "parts", "definition": "d"},
    "operating_hours": {"label": "Hours", "grain": "asset_component", "unit": "hours", "definition": "d"},
    "functional_failures": {"label": "Failures", "grain": "asset_component", "unit": "count", "definition": "d"},
}}


def raw_plant() -> RawDocument:
    return deepcopy(_PLANT)


def raw_losses() -> RawDocument:
    return deepcopy(_LOSSES)


def raw_measures() -> RawDocument:
    return deepcopy(_MEASURES)


def raw_metric(**overrides: object) -> RawDocument:
    """An availability-like metric; keyword arguments replace fields."""
    metric: RawDocument = {"id": "availability", "label": "Availability", "description": "d", "owner": "production",
                           "numerator": "run_time", "denominator": "planned_production_time", "format": "percent",
                           "synonyms": ["uptime share"]}
    return {**metric, **overrides}
