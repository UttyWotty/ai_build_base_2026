"""Generates daily FX rates and the import duty table in both published (source) and canonical forms.

Treasury publishes rates as currency units per USD and duty as a percentage; the ontology stores USD per unit and a fraction.
Canonical values are computed from the rounded published values, so a correct conform step reproduces them exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic.reference_data import (
    CATEGORIES,
    COUNTRIES,
    START_USD_PER_UNIT,
)

BASE_CURRENCY = "USD"
DAILY_LOG_VOLATILITY = 0.004
PUBLISHED_RATE_DECIMALS = 6
# FX history starts before the horizon because inbound shipments leave origin weeks before they are received.
FX_LEAD_IN_DAYS = 120
HIGH_DUTY_ORIGINS = frozenset({"CN"})
HIGH_DUTY_PCT_RANGE = (7.5, 25.0)
STANDARD_DUTY_PCT_RANGE = (0.0, 6.0)
DUTY_PCT_DECIMALS = 2
PERCENT = 100.0


@dataclass(frozen=True)
class FxTable:
    """Canonical USD-per-unit rates indexed by (currency, day offset)."""

    first_day: int
    usd_per_unit: dict[str, np.ndarray]

    def rate(self, currency: str, day: int) -> float:
        """USD value of one unit of `currency` on `day`."""
        return float(self.usd_per_unit[currency][day - self.first_day])


def generate_fx(horizon_days: int, rng: np.random.Generator) -> tuple[pd.DataFrame, FxTable]:
    """Return the published rate table (units per USD, rounded) and the canonical lookup derived from it."""
    first_day = -FX_LEAD_IN_DAYS
    day_count = horizon_days + FX_LEAD_IN_DAYS
    frames, canonical = [], {}
    for currency in sorted({profile.currency for profile in COUNTRIES.values()}):
        if currency == BASE_CURRENCY:
            published = np.ones(day_count)
        else:
            walk = np.cumsum(rng.normal(0.0, DAILY_LOG_VOLATILITY, size=day_count))
            published = np.round(np.exp(walk) / START_USD_PER_UNIT[currency], PUBLISHED_RATE_DECIMALS)
        canonical[currency] = 1.0 / published
        frames.append(pd.DataFrame(
            {"currency": currency, "day": np.arange(first_day, first_day + day_count), "units_per_usd": published}
        ))
    return pd.concat(frames, ignore_index=True), FxTable(first_day, canonical)


def generate_duty_rates(rng: np.random.Generator) -> pd.DataFrame:
    """Return duty by origin country and category, with the published percent and the canonical fraction."""
    rows = []
    for country in sorted(COUNTRIES):
        low, high = HIGH_DUTY_PCT_RANGE if country in HIGH_DUTY_ORIGINS else STANDARD_DUTY_PCT_RANGE
        for category in sorted(CATEGORIES):
            pct = round(float(rng.uniform(low, high)), DUTY_PCT_DECIMALS)
            rows.append((country, category, pct, pct / PERCENT))
    return pd.DataFrame(rows, columns=["origin_country", "category", "duty_rate_pct", "duty_pct"])
