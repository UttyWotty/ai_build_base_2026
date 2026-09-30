"""Supplier behaviour: delivery reliability, date confirmations and revisions, and the planted degradation story.

Each supplier has a base on-time share; the story supplier's share ramps down to the degraded level over one quarter.
Functions take day offsets and the caller's Generator and return plain values, keeping the simulation loop simple.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from supply_ontology.data_pipeline.synthetic.config import StoryConfig
from supply_ontology.data_pipeline.synthetic.timeline import DAYS_PER_WEEK

BASE_ON_TIME_SHARE_RANGE = (0.90, 0.98)
# The first confirmation arrives within these days of the order and lands within +-CONFIRM_SPREAD_DAYS of the contract lead.
CONFIRM_DELAY_DAYS = (1, 3)
CONFIRM_SPREAD_DAYS = 2
REVISION_SHARE = 0.3
REVISION_NOTICE_DAYS = (3, 10)
REVISION_PUSH_DAYS = (3, 14)
EARLY_DAYS_MAX = 2
LATE_DAYS = (1, 10)
CONFIRM_HOURS = (6, 22)


@dataclass(frozen=True)
class Confirmation:
    """A supplier's confirmed delivery day, sent on confirmed_at_day at a local hour."""

    confirmed_day: int
    confirmed_at_day: int
    confirmed_hour: int


def base_on_time_shares(supplier_ids: list[str], rng: np.random.Generator) -> dict[str, float]:
    """Draw a base on-time share per supplier."""
    shares = rng.uniform(*BASE_ON_TIME_SHARE_RANGE, size=len(supplier_ids))
    return {supplier_id: float(share) for supplier_id, share in zip(supplier_ids, shares)}


def on_time_share(base: float, degrading: bool, promised_day: int, stories: StoryConfig) -> float:
    """On-time share for a delivery promised on promised_day, applying the degradation ramp to the story supplier."""
    week = promised_day // DAYS_PER_WEEK
    if not degrading or week < stories.degradation_start_week:
        return base
    progress = min(1.0, (week - stories.degradation_start_week + 1) / stories.degradation_weeks)
    return base + (stories.degraded_on_time_share - base) * progress


def sample_confirmations(order_day: int, lead_days: int, rng: np.random.Generator) -> tuple[Confirmation, ...]:
    """One confirmation, sometimes followed by a later revision that pushes the date out."""
    first_at = order_day + int(rng.integers(CONFIRM_DELAY_DAYS[0], CONFIRM_DELAY_DAYS[1] + 1))
    first_day = order_day + lead_days + int(rng.integers(-CONFIRM_SPREAD_DAYS, CONFIRM_SPREAD_DAYS + 1))
    confirmations = [Confirmation(first_day, first_at, int(rng.integers(*CONFIRM_HOURS)))]
    if rng.random() < REVISION_SHARE:
        revised_at = first_at + int(rng.integers(REVISION_NOTICE_DAYS[0], REVISION_NOTICE_DAYS[1] + 1))
        revised_day = first_day + int(rng.integers(REVISION_PUSH_DAYS[0], REVISION_PUSH_DAYS[1] + 1))
        confirmations.append(Confirmation(revised_day, revised_at, int(rng.integers(*CONFIRM_HOURS))))
    return tuple(confirmations)


def sample_arrival_offset(share: float, rng: np.random.Generator) -> int:
    """Days between promised and actual arrival: zero or negative when on time, positive when late."""
    if rng.random() < share:
        return -int(rng.integers(0, EARLY_DAYS_MAX + 1))
    return int(rng.integers(LATE_DAYS[0], LATE_DAYS[1] + 1))
