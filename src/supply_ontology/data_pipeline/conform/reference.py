"""Conforms treasury FX rates, the trade duty table, and weekly ERP inventory into canonical entities.

Treasury quotes units per USD, so the canonical USD value per unit is the reciprocal; duty percent becomes a fraction.
usd_rates_on returns the rate for each (currency, date) pair and fails on any gap in the FX history.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.data_pipeline.conform import source_layout as layout
from supply_ontology.data_pipeline.conform.dates import as_dates
from supply_ontology.data_pipeline.conform.keys import map_or_fail
from supply_ontology.data_pipeline.conform.source_layout import Sources

PERCENT = 100.0


def conform_fx_rate(sources: Sources) -> pd.DataFrame:
    treasury = sources[layout.TREASURY_FX]
    return pd.DataFrame({
        "currency": treasury["Currency"],
        "rate_date": as_dates(treasury["Date"]),
        "usd_per_unit": 1.0 / treasury["Rate per USD"].astype(float),
    })


def conform_duty_rate(sources: Sources) -> pd.DataFrame:
    trade = sources[layout.TRADE_DUTY]
    return pd.DataFrame({
        "origin_country": trade["Origin"],
        "category": trade["Category"],
        "duty_pct": trade["Duty %"].astype(float) / PERCENT,
    })


def conform_inventory_snapshot(sources: Sources) -> pd.DataFrame:
    erp = sources[layout.ERP_INVENTORY]
    return pd.DataFrame({
        "plant_id": erp["PLANT"].astype(str),
        "part_id": erp["MATERIAL"].astype(str),
        "snapshot_date": as_dates(erp["WEEK_ENDING"]),
        "qty_on_hand": erp["UNRESTRICTED_QTY"].astype(int),
    })


def usd_rates_on(fx_rate: pd.DataFrame, currencies: pd.Series, dates: pd.Series) -> pd.Series:
    """USD per unit for each (currency, date) pair, aligned with the inputs."""
    lookup = fx_rate.set_index(["currency", "rate_date"])["usd_per_unit"]
    keys = pd.Series(list(zip(currencies, dates)), index=currencies.index)
    return map_or_fail(keys, lookup, "FX rate for (currency, date)").astype(float)
