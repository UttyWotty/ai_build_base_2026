"""Generates master data: plants, suppliers, parts, customers, supplier contracts, and plant stocking plans.

All randomness comes from the caller's numpy Generator, so results are reproducible from the seed.
Output columns use canonical ontology names, plus a few generator-only columns documented on the Masters class.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic import ids
from supply_ontology.data_pipeline.synthetic.config import ScaleConfig
from supply_ontology.data_pipeline.synthetic.errors import GenerationError
from supply_ontology.data_pipeline.synthetic.reference_data import (
    CASE_PACK_SIZES,
    CASE_PACKED_CATEGORY,
    CATEGORIES,
    COMPANY_SUFFIX,
    COUNTRIES,
    CUSTOMER_COUNTRY_WEIGHTS,
    CUSTOMER_NAME_STEMS,
    CUSTOMER_NAME_TRADES,
    EACH_UOM,
    LEAD_TIME_DAYS_BY_REGION,
    MOQ_CHOICES,
    PLANTS,
    SEGMENT_WEIGHTS,
    SEGMENTS,
    START_USD_PER_UNIT,
    SUPPLIER_COUNTRY_WEIGHTS,
    SUPPLIER_NAME_STEMS,
    SUPPLIER_NAME_TRADES,
)

TIER_ONE_SHARE = 0.8
SECOND_SUPPLIER_SHARE = 0.35
# Zipf-like exponent: a few suppliers carry most parts, as in real supply bases.
SUPPLIER_CONCENTRATION = 0.9
PRICE_TO_COST_RANGE = (0.55, 0.80)
WEEKLY_DEMAND_MEDIAN_UNITS = 40.0
WEEKLY_DEMAND_SIGMA = 0.8
MIN_WEEKLY_DEMAND_UNITS = 3.0
PRICE_DECIMALS = 4
COST_DECIMALS = 4
PART_TYPE_CODE_RANGE = (100, 1000)


@dataclass(frozen=True)
class Masters:
    """Master data frames.

    parts carries a generator-only `case_pack` column (1 for parts not moved in cases).
    stocking has one row per (plant_id, part_id) with `weekly_demand_units` and the primary `supplier_id`.
    """

    plants: pd.DataFrame
    suppliers: pd.DataFrame
    parts: pd.DataFrame
    customers: pd.DataFrame
    supplier_parts: pd.DataFrame
    stocking: pd.DataFrame


def generate_masters(scale: ScaleConfig, rng: np.random.Generator) -> Masters:
    """Generate every master data frame for the given scale."""
    plants = pd.DataFrame(
        [(p.plant_id, p.plant_name, p.country, COUNTRIES[p.country].region) for p in PLANTS],
        columns=["plant_id", "plant_name", "country", "region"],
    )
    suppliers = _generate_suppliers(scale.supplier_count, rng)
    parts = _generate_parts(scale.part_count, rng)
    customers = _generate_customers(scale.customer_count, rng)
    supplier_parts = _generate_supplier_parts(suppliers, parts, rng)
    stocking = _generate_stocking(parts, plants, supplier_parts, scale.two_plant_share, rng)
    return Masters(plants, suppliers, parts, customers, supplier_parts, stocking)


def _weighted_countries(weights: dict[str, float], count: int, rng: np.random.Generator) -> list[str]:
    codes = sorted(weights)
    probabilities = np.array([weights[code] for code in codes], dtype=float)
    return [codes[i] for i in rng.choice(len(codes), size=count, p=probabilities / probabilities.sum())]


def _unique_names(stems: tuple[str, ...], trades: tuple[str, ...], count: int, rng: np.random.Generator) -> list[str]:
    combos = [f"{stem} {trade}" for stem, trade in product(stems, trades)]
    if count > len(combos):
        raise GenerationError(f"Requested {count} names but only {len(combos)} unique combinations exist")
    return [combos[i] for i in rng.choice(len(combos), size=count, replace=False)]


def _generate_suppliers(count: int, rng: np.random.Generator) -> pd.DataFrame:
    countries = _weighted_countries(SUPPLIER_COUNTRY_WEIGHTS, count, rng)
    names = _unique_names(SUPPLIER_NAME_STEMS, SUPPLIER_NAME_TRADES, count, rng)
    tiers = np.where(rng.random(count) < TIER_ONE_SHARE, 1, 2)
    return pd.DataFrame(
        {
            "supplier_id": [ids.supplier_id(i) for i in range(count)],
            "supplier_name": [f"{name} {COMPANY_SUFFIX[c]}" for name, c in zip(names, countries)],
            "country": countries,
            "region": [COUNTRIES[c].region for c in countries],
            "tier": tiers.astype(int),
            "currency": [COUNTRIES[c].currency for c in countries],
        }
    )


def _generate_parts(count: int, rng: np.random.Generator) -> pd.DataFrame:
    category_names = sorted(CATEGORIES)
    rows = []
    for index in range(count):
        category = category_names[int(rng.integers(len(category_names)))]
        families, (low, high) = CATEGORIES[category]
        family = families[int(rng.integers(len(families)))]
        cost = float(np.exp(rng.uniform(np.log(low), np.log(high))))
        case_pack = int(rng.choice(CASE_PACK_SIZES)) if category == CASE_PACKED_CATEGORY else 1
        type_code = int(rng.integers(*PART_TYPE_CODE_RANGE))
        rows.append(
            (ids.part_id(index), f"{family} type {type_code}", category, family, EACH_UOM,
             round(cost, COST_DECIMALS), case_pack)
        )
    return pd.DataFrame(
        rows, columns=["part_id", "description", "category", "family", "uom", "standard_cost_usd", "case_pack"]
    )


def _generate_customers(count: int, rng: np.random.Generator) -> pd.DataFrame:
    countries = _weighted_countries(CUSTOMER_COUNTRY_WEIGHTS, count, rng)
    names = _unique_names(CUSTOMER_NAME_STEMS, CUSTOMER_NAME_TRADES, count, rng)
    segments = rng.choice(len(SEGMENTS), size=count, p=np.array(SEGMENT_WEIGHTS))
    return pd.DataFrame(
        {
            "customer_id": [ids.customer_id(i) for i in range(count)],
            "customer_name": [f"{name} {COMPANY_SUFFIX[c]}" for name, c in zip(names, countries)],
            "segment": [SEGMENTS[s] for s in segments],
            "country": countries,
            "region": [COUNTRIES[c].region for c in countries],
        }
    )


def _generate_supplier_parts(suppliers: pd.DataFrame, parts: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    weights = 1.0 / np.arange(1, len(suppliers) + 1) ** SUPPLIER_CONCENTRATION
    weights = weights / weights.sum()
    rows = []
    for part in parts.itertuples(index=False):
        supplier_count = 2 if rng.random() < SECOND_SUPPLIER_SHARE else 1
        for supplier_index in rng.choice(len(suppliers), size=supplier_count, replace=False, p=weights):
            supplier = suppliers.iloc[int(supplier_index)]
            price_usd = part.standard_cost_usd * rng.uniform(*PRICE_TO_COST_RANGE)
            low, high = LEAD_TIME_DAYS_BY_REGION[supplier.region]
            rows.append(
                (supplier.supplier_id, part.part_id,
                 round(price_usd / START_USD_PER_UNIT[supplier.currency], PRICE_DECIMALS),
                 int(rng.choice(MOQ_CHOICES)), int(rng.integers(low, high + 1)))
            )
    return pd.DataFrame(
        rows, columns=["supplier_id", "part_id", "unit_price_local", "moq", "contracted_lead_time_days"]
    )


def _generate_stocking(
    parts: pd.DataFrame, plants: pd.DataFrame, supplier_parts: pd.DataFrame,
    two_plant_share: float, rng: np.random.Generator,
) -> pd.DataFrame:
    primary_supplier = supplier_parts.groupby("part_id", sort=False)["supplier_id"].first()
    plant_ids = plants["plant_id"].tolist()
    rows = []
    for part_id in parts["part_id"]:
        plant_count = 2 if rng.random() < two_plant_share else 1
        for plant_index in sorted(rng.choice(len(plant_ids), size=plant_count, replace=False)):
            demand = rng.lognormal(np.log(WEEKLY_DEMAND_MEDIAN_UNITS), WEEKLY_DEMAND_SIGMA)
            rows.append((plant_ids[int(plant_index)], part_id, max(MIN_WEEKLY_DEMAND_UNITS, float(demand)),
                         primary_supplier[part_id]))
    return pd.DataFrame(rows, columns=["plant_id", "part_id", "weekly_demand_units", "supplier_id"])
