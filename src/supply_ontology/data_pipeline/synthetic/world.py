"""Orchestrates world generation: masters, FX, demand, simulation, logistics, then canonical table assembly.

A single numpy Generator seeded from the config drives every random draw, in a fixed order, so worlds are reproducible.
The result holds the canonical truth tables (ontology entities) plus the extras that source renderers need.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count

import numpy as np
import pandas as pd

from supply_ontology.data_pipeline.synthetic.config import GenerationConfig
from supply_ontology.data_pipeline.synthetic.demand import generate_sales_lines
from supply_ontology.data_pipeline.synthetic.fx import generate_duty_rates, generate_fx
from supply_ontology.data_pipeline.synthetic.inventory_sim import (
    ComboPlan,
    SimRecords,
    simulate_combo,
)
from supply_ontology.data_pipeline.synthetic.logistics import (
    build_inbound,
    build_outbound,
)
from supply_ontology.data_pipeline.synthetic.masters import Masters, generate_masters
from supply_ontology.data_pipeline.synthetic.supplier_behavior import (
    base_on_time_shares,
)
from supply_ontology.data_pipeline.synthetic.timeline import DAYS_PER_WEEK, Timeline
from supply_ontology.data_pipeline.synthetic.world_tables import (
    WorldExtras,
    assemble_world,
    number_purchase_orders,
    number_receipts,
)

SAFETY_WEEKS = 1.5
CYCLE_WEEKS = 3.0


@dataclass(frozen=True)
class StoryFacts:
    """Facts about the planted stories that are decided during generation."""

    degrading_supplier_id: str


@dataclass(frozen=True)
class World:
    """Canonical truth tables keyed by ontology entity name, plus renderer extras."""

    tables: dict[str, pd.DataFrame]
    extras: WorldExtras
    story_facts: StoryFacts
    timeline: Timeline


def build_world(config: GenerationConfig) -> World:
    """Generate the complete world for a config."""
    rng = np.random.default_rng(config.seed)
    timeline = Timeline(config.horizon_start, config.scale.weeks)
    masters = generate_masters(config.scale, rng)
    fx_published, fx = generate_fx(config.scale.weeks * DAYS_PER_WEEK, rng)
    duty = generate_duty_rates(rng)
    sales_lines = generate_sales_lines(masters, config.scale, config.stories, rng)
    degrading_supplier = _degrading_supplier(masters)
    records = _simulate(masters, sales_lines, degrading_supplier, config, rng)
    po_lines = number_purchase_orders(records, masters)
    receipts = number_receipts(records, po_lines)
    cost = masters.parts.set_index("part_id")["standard_cost_usd"]
    allocations = _allocations_frame(records, sales_lines, cost)
    outbound, outbound_keys = build_outbound(
        allocations, masters.plants, masters.customers, fx, timeline.weeks * DAYS_PER_WEEK - 1, rng
    )
    receipts = receipts.assign(goods_value_usd=receipts["qty"] * receipts["part_id"].map(cost).to_numpy())
    inbound, inbound_keys = build_inbound(receipts, masters.suppliers, masters.plants, config.stories, fx, rng)
    tables, extras = assemble_world(
        masters=masters, timeline=timeline, sales_lines=sales_lines, po_lines=po_lines,
        receipts=receipts.assign(shipment_key=inbound_keys.to_numpy()),
        allocations=allocations.assign(shipment_key=outbound_keys.to_numpy()),
        shipments=pd.concat([inbound, outbound], ignore_index=True),
        confirmations=pd.DataFrame(records.confirmations, columns=["po_seq", "confirmed_day", "confirmed_at_day", "confirmed_hour", "sequence"]),
        snapshots=pd.DataFrame(records.snapshots, columns=["plant_id", "part_id", "day", "qty_on_hand"]),
        fx_published=fx_published, duty=duty, rng=rng,
    )
    return World(tables, extras, StoryFacts(degrading_supplier), timeline)


def _degrading_supplier(masters: Masters) -> str:
    """The supplier that is primary for the most plant-part combinations (lowest id on ties)."""
    counts = masters.stocking.groupby("supplier_id").size()
    return str(counts[counts == counts.max()].index.min())


def _simulate(
    masters: Masters, sales_lines: pd.DataFrame, degrading_supplier: str,
    config: GenerationConfig, rng: np.random.Generator,
) -> SimRecords:
    stories = config.stories
    shares = base_on_time_shares(sorted(masters.suppliers["supplier_id"]), rng)
    terms = masters.supplier_parts.set_index(["supplier_id", "part_id"])
    category = masters.parts.set_index("part_id")["category"]
    open_lines = sales_lines[~sales_lines["cancelled"]]
    lines_by_combo = dict(tuple(open_lines.groupby(["plant_id", "part_id"], sort=True)))
    records, po_sequence = SimRecords(), count()
    empty = open_lines.iloc[0:0]
    for combo in masters.stocking.itertuples(index=False):
        contract = terms.loc[(combo.supplier_id, combo.part_id)]
        overstock = combo.plant_id == stories.overstock_plant_id and category[combo.part_id] == stories.overstock_category
        multiplier = stories.overstock_multiplier if overstock else 1.0
        weekly = combo.weekly_demand_units
        reorder_point = weekly * (contract.contracted_lead_time_days / DAYS_PER_WEEK + SAFETY_WEEKS) * multiplier
        plan = ComboPlan(
            plant_id=combo.plant_id, part_id=combo.part_id, supplier_id=combo.supplier_id,
            lead_days=int(contract.contracted_lead_time_days), moq=int(contract.moq),
            base_on_time_share=shares[combo.supplier_id], degrading=combo.supplier_id == degrading_supplier,
            reorder_point=reorder_point, order_up_to=reorder_point + weekly * CYCLE_WEEKS * multiplier,
        )
        lines = lines_by_combo.get((combo.plant_id, combo.part_id), empty)
        simulate_combo(plan, lines, config.scale.weeks, stories, rng, records, po_sequence)
    return records


def _allocations_frame(records: SimRecords, sales_lines: pd.DataFrame, cost: pd.Series) -> pd.DataFrame:
    allocations = pd.DataFrame(records.allocations, columns=["so_line_id", "ship_day", "qty"])
    line_info = sales_lines.set_index("so_line_id")[["plant_id", "customer_id", "part_id"]]
    allocations = allocations.join(line_info, on="so_line_id")
    return allocations.assign(goods_value_usd=allocations["qty"] * allocations["part_id"].map(cost).to_numpy())
