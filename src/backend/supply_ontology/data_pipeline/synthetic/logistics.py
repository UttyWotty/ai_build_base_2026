"""Builds inbound and outbound shipments with carriers, transit, delays, and freight, including the freight-spike story.

Outbound allocations are grouped per plant, customer, and ship day; inbound receipts per supplier, plant, and receipt day.
Freight is billed in the plant's currency, and the canonical USD amount is derived from that billed amount and the published FX rate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic.config import StoryConfig
from supply_ontology.data_pipeline.synthetic.fx import FxTable
from supply_ontology.data_pipeline.synthetic.reference_data import (
    CARRIER_ON_TIME_SHARE,
    CARRIERS_BY_REGION,
    COUNTRIES,
    FREIGHT_BASE_USD,
    FULL_LOAD_VALUE_USD,
    INTERCONTINENTAL,
    MIN_LOAD_SHARE,
    OCEAN_CARRIERS,
    TRANSIT_DAYS,
    lane_class,
)
from supply_ontology.data_pipeline.synthetic.timeline import DAYS_PER_WEEK

INBOUND, OUTBOUND = "inbound", "outbound"
FREIGHT_NOISE = (0.85, 1.15)
OUTBOUND_VALUE_SHARE = 0.02
INBOUND_VALUE_SHARE = 0.03
EARLY_DAYS_MAX = 1
ROAD_LATE_DAYS = (1, 4)
OCEAN_LATE_DAYS = (2, 10)
EVENT_HOURS = (6, 21)
MONEY_DECIMALS = 2

SHIPMENT_COLUMNS = [
    "shipment_key", "direction", "carrier", "origin", "destination", "origin_country", "destination_country",
    "ship_day", "planned_delivery_day", "delivered_day", "freight_amount_local", "freight_currency",
    "freight_cost_usd", "pickup_hour", "delivery_hour",
]


def build_outbound(
    allocations: pd.DataFrame, plants: pd.DataFrame, customers: pd.DataFrame,
    fx: FxTable, horizon_end_day: int, rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.Series]:
    """Group allocations (so_line_id, ship_day, qty, plant_id, customer_id, goods_value_usd) into shipments.

    Returns the shipment frame and, aligned with `allocations`, the shipment_key of each allocation.
    """
    keys = ["plant_id", "customer_id", "ship_day"]
    groups = allocations.groupby(keys, sort=True).agg(goods_value_usd=("goods_value_usd", "sum")).reset_index()
    groups["shipment_key"] = OUTBOUND + ":" + pd.RangeIndex(len(groups)).astype(str)
    origin_country = groups["plant_id"].map(plants.set_index("plant_id")["country"])
    destination_country = groups["customer_id"].map(customers.set_index("customer_id")["country"])
    shipments = _finish(
        groups, OUTBOUND, groups["plant_id"], groups["customer_id"], origin_country, destination_country,
        billing_currency=origin_country.map(lambda c: COUNTRIES[c].currency), value_share=OUTBOUND_VALUE_SHARE,
        spike=np.ones(len(groups)), fx=fx, rng=rng,
    )
    delivered = shipments["delivered_day"]
    shipments["delivered_day"] = delivered.where(delivered <= horizon_end_day).astype("Int64")
    key_of = allocations.merge(groups[keys + ["shipment_key"]], on=keys, how="left")["shipment_key"]
    return shipments, key_of


def build_inbound(
    receipts: pd.DataFrame, suppliers: pd.DataFrame, plants: pd.DataFrame,
    stories: StoryConfig, fx: FxTable, rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.Series]:
    """Group receipts (supplier_id, plant_id, receipt_day, goods_value_usd) into inbound shipments.

    Delivery is the receipt day; the ship day is back-calculated from nominal transit plus the carrier delay.
    """
    keys = ["supplier_id", "plant_id", "receipt_day"]
    groups = receipts.groupby(keys, sort=True).agg(goods_value_usd=("goods_value_usd", "sum")).reset_index()
    groups["shipment_key"] = INBOUND + ":" + pd.RangeIndex(len(groups)).astype(str)
    origin_country = groups["supplier_id"].map(suppliers.set_index("supplier_id")["country"])
    destination_country = groups["plant_id"].map(plants.set_index("plant_id")["country"])
    groups["ship_day"] = groups["receipt_day"]
    shipments = _finish(
        groups, INBOUND, groups["supplier_id"], groups["plant_id"], origin_country, destination_country,
        billing_currency=destination_country.map(lambda c: COUNTRIES[c].currency), value_share=INBOUND_VALUE_SHARE,
        spike=np.ones(len(groups)), fx=None, rng=rng,
    )
    # Delivered on the receipt day: move ship and planned days back by nominal transit plus the carrier delay.
    nominal = shipments["planned_delivery_day"] - shipments["ship_day"]
    delay = shipments["delivered_day"] - shipments["planned_delivery_day"]
    receipt_day = groups["receipt_day"].to_numpy()
    shipments["delivered_day"] = receipt_day
    shipments["ship_day"] = receipt_day - nominal - delay
    shipments["planned_delivery_day"] = shipments["ship_day"] + nominal
    spike = _spike_multiplier(shipments, stories)
    _price_freight(shipments, groups["goods_value_usd"].to_numpy(), INBOUND_VALUE_SHARE, spike, fx, rng)
    key_of = receipts.merge(groups[keys + ["shipment_key"]], on=keys, how="left")["shipment_key"]
    return shipments, key_of


def _nominal(shipments: pd.DataFrame) -> pd.Series:
    return pd.Series(
        [TRANSIT_DAYS[lane_class(o, d)] for o, d in zip(shipments["origin_country"], shipments["destination_country"])],
        index=shipments.index,
    )


def _finish(
    groups: pd.DataFrame, direction: str, origin: pd.Series, destination: pd.Series,
    origin_country: pd.Series, destination_country: pd.Series, billing_currency: pd.Series,
    value_share: float, spike: np.ndarray, fx: FxTable | None, rng: np.random.Generator,
) -> pd.DataFrame:
    count = len(groups)
    shipments = pd.DataFrame({
        "shipment_key": groups["shipment_key"], "direction": direction, "origin": origin, "destination": destination,
        "origin_country": origin_country, "destination_country": destination_country,
        "ship_day": groups["ship_day"].to_numpy(), "freight_currency": billing_currency,
    })
    shipments["carrier"] = _pick_carriers(origin_country, destination_country, rng)
    nominal = _nominal(shipments)
    shipments["planned_delivery_day"] = shipments["ship_day"] + nominal
    shipments["delivered_day"] = shipments["planned_delivery_day"] + _carrier_delays(shipments["carrier"], rng)
    shipments["pickup_hour"] = rng.integers(*EVENT_HOURS, size=count)
    shipments["delivery_hour"] = rng.integers(*EVENT_HOURS, size=count)
    if fx is not None:
        _price_freight(shipments, groups["goods_value_usd"].to_numpy(), value_share, spike, fx, rng)
    return shipments


def _pick_carriers(origin_country: pd.Series, destination_country: pd.Series, rng: np.random.Generator) -> list[str]:
    carriers = []
    for origin, destination in zip(origin_country, destination_country):
        if lane_class(origin, destination) == INTERCONTINENTAL:
            options = OCEAN_CARRIERS
        else:
            options = CARRIERS_BY_REGION[COUNTRIES[origin].region]
        carriers.append(options[int(rng.integers(len(options)))])
    return carriers


def _carrier_delays(carriers: pd.Series, rng: np.random.Generator) -> np.ndarray:
    delays = np.empty(len(carriers), dtype=int)
    draws = rng.random(len(carriers))
    for index, carrier in enumerate(carriers):
        if draws[index] < CARRIER_ON_TIME_SHARE[carrier]:
            delays[index] = -int(rng.integers(0, EARLY_DAYS_MAX + 1))
        else:
            low, high = OCEAN_LATE_DAYS if carrier in OCEAN_CARRIERS else ROAD_LATE_DAYS
            delays[index] = int(rng.integers(low, high + 1))
    return delays


def _spike_multiplier(shipments: pd.DataFrame, stories: StoryConfig) -> np.ndarray:
    week = shipments["ship_day"].to_numpy() // DAYS_PER_WEEK
    in_window = (week >= stories.freight_spike_start_week) & (
        week < stories.freight_spike_start_week + stories.freight_spike_weeks
    )
    on_lane = (shipments["origin_country"] == stories.freight_spike_origin_country).to_numpy() & (
        shipments["destination"] == stories.freight_spike_plant_id
    ).to_numpy()
    return np.where(in_window & on_lane, stories.freight_spike_multiplier, 1.0)


def _price_freight(
    shipments: pd.DataFrame, goods_value_usd: np.ndarray, value_share: float,
    spike: np.ndarray, fx: FxTable, rng: np.random.Generator,
) -> None:
    lanes = [lane_class(o, d) for o, d in zip(shipments["origin_country"], shipments["destination_country"])]
    base = np.array([FREIGHT_BASE_USD[lane] for lane in lanes])
    full_load = np.array([FULL_LOAD_VALUE_USD[lane] for lane in lanes])
    load_share = np.clip(goods_value_usd / full_load, MIN_LOAD_SHARE, 1.0)
    usd = (base * load_share * rng.uniform(*FREIGHT_NOISE, size=len(shipments)) + value_share * goods_value_usd) * spike
    rates = np.array([fx.rate(c, int(d)) for c, d in zip(shipments["freight_currency"], shipments["ship_day"])])
    local = np.round(usd / rates, MONEY_DECIMALS)
    shipments["freight_amount_local"] = local
    shipments["freight_cost_usd"] = local * rates
