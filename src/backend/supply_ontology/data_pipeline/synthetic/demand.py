"""Generates customer demand: sales order lines with requested and committed dates, grouped into orders.

Lines are drawn per plant-part combination and week, then assigned to customers with a preference for the plant's region.
All dates are integer day offsets from the horizon start; conversion to calendar dates happens at assembly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic import ids
from supply_ontology.data_pipeline.synthetic.config import ScaleConfig, StoryConfig
from supply_ontology.data_pipeline.synthetic.masters import Masters
from supply_ontology.data_pipeline.synthetic.reference_data import (
    TRANSIT_DAYS,
    lane_class,
)
from supply_ontology.data_pipeline.synthetic.timeline import DAYS_PER_WEEK

WORKDAYS_PER_WEEK = 5
SAME_REGION_PREFERENCE = 4.0
CUSTOMER_SIZE_CONCENTRATION = 0.8
# Requested lead time in days on top of transit, by segment; the short-request segment ignores transit (story config).
REQUESTED_LEAD_DAYS = {"OEM": (14, 35), "Distributor": (10, 28)}
SHORT_REQUEST_LEAD_DAYS = (3, 8)
HANDLING_DAYS = 3
# Plants plan to ship this many days before the committed date minus transit, absorbing small carrier delays.
SHIP_BUFFER_DAYS = 2
SLIP_SHARE = 0.2
SLIP_DAYS = (2, 7)
CANCELLED_LINE_SHARE = 0.02
LINE_QTY_GAMMA_SHAPE = 2.0
DEMAND_RATE_EXPONENT = 0.5
MIN_SHIP_LEAD_DAYS = 1

SALES_LINE_COLUMNS = [
    "so_line_id", "so_id", "customer_id", "part_id", "plant_id", "qty_ordered", "order_day",
    "requested_day", "committed_day", "planned_ship_day", "cancelled",
]


def generate_sales_lines(
    masters: Masters, scale: ScaleConfig, stories: StoryConfig, rng: np.random.Generator
) -> pd.DataFrame:
    """Return every sales order line with day offsets and assigned order ids."""
    raw = _draw_lines(masters, scale, rng)
    raw = _assign_customers(raw, masters, rng)
    raw = _assign_dates(raw, masters, stories, rng)
    return _group_into_orders(raw)


def _draw_lines(masters: Masters, scale: ScaleConfig, rng: np.random.Generator) -> pd.DataFrame:
    stocking = masters.stocking
    weights = stocking["weekly_demand_units"].to_numpy() ** DEMAND_RATE_EXPONENT
    lines_per_week = scale.sales_lines_per_week * weights / weights.sum()
    counts = rng.poisson(np.repeat(lines_per_week[:, None], scale.weeks, axis=1))
    combo_index, week = np.nonzero(counts)
    repeats = counts[combo_index, week]
    combo_index, week = np.repeat(combo_index, repeats), np.repeat(week, repeats)
    mean_qty = stocking["weekly_demand_units"].to_numpy()[combo_index] / lines_per_week[combo_index]
    qty = np.maximum(1, np.round(rng.gamma(LINE_QTY_GAMMA_SHAPE, mean_qty / LINE_QTY_GAMMA_SHAPE)))
    case_pack = masters.parts.set_index("part_id")["case_pack"]
    part_ids = stocking["part_id"].to_numpy()[combo_index]
    packs = case_pack.loc[part_ids].to_numpy()
    qty = (np.ceil(qty / packs) * packs).astype(int)
    return pd.DataFrame(
        {
            "plant_id": stocking["plant_id"].to_numpy()[combo_index],
            "part_id": part_ids,
            "qty_ordered": qty,
            "order_day": week * DAYS_PER_WEEK + rng.integers(0, WORKDAYS_PER_WEEK, size=len(week)),
        }
    )


def _assign_customers(lines: pd.DataFrame, masters: Masters, rng: np.random.Generator) -> pd.DataFrame:
    customers = masters.customers
    size = 1.0 / np.arange(1, len(customers) + 1) ** CUSTOMER_SIZE_CONCENTRATION
    plant_region = masters.plants.set_index("plant_id")["region"]
    assigned = np.empty(len(lines), dtype=object)
    for plant_id in sorted(lines["plant_id"].unique()):
        mask = (lines["plant_id"] == plant_id).to_numpy()
        preference = np.where(customers["region"] == plant_region[plant_id], SAME_REGION_PREFERENCE, 1.0)
        probabilities = size * preference
        picks = rng.choice(len(customers), size=int(mask.sum()), p=probabilities / probabilities.sum())
        assigned[mask] = customers["customer_id"].to_numpy()[picks]
    return lines.assign(customer_id=assigned)


def _assign_dates(
    lines: pd.DataFrame, masters: Masters, stories: StoryConfig, rng: np.random.Generator
) -> pd.DataFrame:
    customers = masters.customers.set_index("customer_id")
    plant_country = masters.plants.set_index("plant_id")["country"]
    segment = customers.loc[lines["customer_id"], "segment"].to_numpy()
    transit = np.array(
        [TRANSIT_DAYS[lane_class(plant_country[p], customers.at[c, "country"])]
         for p, c in zip(lines["plant_id"], lines["customer_id"])]
    )
    request_lead = np.empty(len(lines), dtype=int)
    for name in np.unique(segment):
        short = name == stories.short_request_segment
        low, high = SHORT_REQUEST_LEAD_DAYS if short else REQUESTED_LEAD_DAYS[name]
        mask = segment == name
        request_lead[mask] = rng.integers(low, high + 1, size=int(mask.sum())) + (0 if short else transit[mask])
    order_day = lines["order_day"].to_numpy()
    requested = order_day + request_lead
    earliest_commit = order_day + HANDLING_DAYS + transit
    slip = np.where(rng.random(len(lines)) < SLIP_SHARE, rng.integers(SLIP_DAYS[0], SLIP_DAYS[1] + 1, len(lines)), 0)
    committed = np.maximum(requested, earliest_commit) + slip
    return lines.assign(
        requested_day=requested,
        committed_day=committed,
        planned_ship_day=np.maximum(order_day + MIN_SHIP_LEAD_DAYS, committed - transit - SHIP_BUFFER_DAYS),
        cancelled=rng.random(len(lines)) < CANCELLED_LINE_SHARE,
    )


def _group_into_orders(lines: pd.DataFrame) -> pd.DataFrame:
    ordered = lines.sort_values(
        ["order_day", "customer_id", "plant_id", "part_id", "qty_ordered"], kind="mergesort"
    ).reset_index(drop=True)
    order_key = ordered["order_day"].astype(str) + "|" + ordered["customer_id"]
    order_index = pd.factorize(order_key)[0]
    item = (ordered.groupby(order_index).cumcount() + 1) * ids.SO_ITEM_STEP
    so_ids = [ids.so_number(i) for i in order_index]
    return ordered.assign(
        so_id=so_ids,
        so_line_id=[ids.so_line_id(so, int(n)) for so, n in zip(so_ids, item)],
    )[SALES_LINE_COLUMNS]
