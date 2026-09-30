"""The seasonal coolant temperature rise shared by the sensor model and the scrap model.

Coolant runs warmer in summer everywhere, and much warmer on the coolant story line.
Keeping one function means the scrap the MES reports and the temperature the historian shows move together.
"""
from __future__ import annotations

import numpy as np

from pdm_oee.data_pipeline.synthetic.reference import (
    COOLANT_SEASONAL_RISE,
    SUMMER_PEAK_DAY_OF_YEAR,
)

DAYS_PER_YEAR = 365.25
HALF = 0.5


def coolant_rise(day_of_year: np.ndarray, story_line: bool, story_rise: float) -> np.ndarray:
    """Degrees C above the normal coolant temperature: a cosine peaking in summer, never negative."""
    season = np.cos(2 * np.pi * (day_of_year - SUMMER_PEAK_DAY_OF_YEAR) / DAYS_PER_YEAR)
    amplitude = story_rise if story_line else COOLANT_SEASONAL_RISE
    return amplitude * np.clip(season, 0.0, None) * (1 + HALF * season) / (1 + HALF)
