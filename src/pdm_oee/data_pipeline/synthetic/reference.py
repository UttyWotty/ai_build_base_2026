"""Static facts of the fictional plant that the catalog does not govern: sites, layout, products, and behaviour rates.

Failure modes, sensor ranges, P-F intervals, and repair times come from the governed plant model instead.
Site-specific codes here are what the source systems print; the conform step maps them back to governed ids.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SiteSpec:
    """One site's clock, units, and the codes its systems use."""

    site_id: str
    number: int
    timezone: str
    imperial_units: bool
    state_codes: dict[str, str]
    reason_codes: dict[str, str]
    good_quality: object
    bad_quality: object


# Governed state -> code printed by the site's MES.
_US_STATES = {"running": "RUN", "planned_stop": "PLN", "unplanned_stop": "DWN"}
_DE_STATES = {"running": "PROD", "planned_stop": "GEPLANT", "unplanned_stop": "STOERUNG"}
_US_REASONS = {"scheduled_break": "BRK", "planned_maintenance": "PM", "no_production_scheduled": "NOSCHED",
               "equipment_failure": "BD-MECH", "electrical_fault": "BD-ELEC", "changeover": "CO", "tool_change": "TC",
               "adjustment": "ADJ", "material_starved": "STRV", "output_blocked": "BLKD", "no_operator": "NOOP"}
_DE_REASONS = {"scheduled_break": "P01", "planned_maintenance": "P02", "no_production_scheduled": "P03",
               "equipment_failure": "S10", "electrical_fault": "S11", "changeover": "R20", "tool_change": "R21",
               "adjustment": "R22", "material_starved": "E30", "output_blocked": "E31", "no_operator": "E32"}
# OPC-style numeric quality at US1, text quality at DE1.
SITES = (
    SiteSpec("US1", 1, "America/Chicago", True, _US_STATES, _US_REASONS, 192, 0),
    SiteSpec("DE1", 2, "Europe/Berlin", False, _DE_STATES, _DE_REASONS, "Good", "Bad"),
)

# Position on a line -> (asset class, short code used in historian tags).
LINE_LAYOUT = ((1, "cnc_machining_centre", "CNC01"), (2, "cnc_machining_centre", "CNC02"),
               (3, "hydraulic_press", "PRS01"), (4, "conveyor_drive", "CNV01"))
CRITICALITY = {"cnc_machining_centre": "A", "hydraulic_press": "A", "conveyor_drive": "B"}
# One product family per line, in line order per site.
FAMILIES = {"US1": ("valve_bodies", "pump_housings", "gear_blanks"), "DE1": ("brackets", "flanges", "shafts")}
PRODUCT_PREFIX = {"valve_bodies": "VB", "pump_housings": "PH", "gear_blanks": "GB",
                  "brackets": "BR", "flanges": "FL", "shafts": "SH"}
PRODUCT_VARIANTS = ((100, 0.8), (200, 1.0), (300, 1.3))
BASE_CYCLE_SECONDS = {"cnc_machining_centre": 150.0, "hydraulic_press": 30.0, "conveyor_drive": 20.0}
# Nameplate cycle = fastest product's ideal cycle x this factor (brochure speed is optimistic).
NAMEPLATE_FACTOR = 0.85

# Shifts, breaks, holidays (local time).
SHIFT_START_HOURS = (6, 14, 22)
SHIFT_HOURS = 8
PRODUCTION_WEEKDAYS = 5
BREAK_OFFSET_MINUTES = 240
BREAK_MINUTES = 30
HOLIDAYS = ((12, 24), (12, 25), (12, 26), (12, 31), (1, 1))

# Reliability: mean days from restoration (plus the baseline window) to the next failure onset, per failure mode.
MEAN_DAYS_TO_ONSET = {"spindle_bearing_wear": 110.0, "coolant_pump_cavitation": 140.0, "tool_changer_jam": 25.0,
                      "hydraulic_pump_wear": 170.0, "main_seal_leak": 120.0, "gearbox_wear": 150.0,
                      "motor_overheating": 160.0}
BASELINE_WINDOW_DAYS = 14
PF_VARIATION = (0.8, 1.2)
REPAIR_VARIATION = (0.9, 1.5)
RESPONSE_HOURS = (0.5, 3.0)

# Preventive maintenance: routine service that does not reset component wear.
PM_INTERVAL_DAYS = {"cnc_machining_centre": 42, "hydraulic_press": 56, "conveyor_drive": 70}
PM_HOURS = {"cnc_machining_centre": 3.0, "hydraulic_press": 4.0, "conveyor_drive": 2.0}
PM_LATE_SHARE = 0.1
PM_LATE_DAYS = (1, 10)

# Operations: (events per shift or per hour, (min, max) minutes).
CHANGEOVER_MINUTES = (30, 60)
ORDER_SHIFTS = (3, 9)
TOOL_CHANGES_PER_SHIFT = 2.0
TOOL_CHANGE_MINUTES = (6, 12)
ADJUSTMENTS_PER_SHIFT = 1.0
ADJUSTMENT_MINUTES = (5, 15)
EXTERNAL_STOPS_PER_SHIFT = 0.5
EXTERNAL_STOP_MINUTES = (5, 25)
SMALL_STOPS_PER_HOUR = 0.5
SMALL_STOP_MINUTES = (1, 4)
SPEED_FACTOR = (1.02, 1.12)
BASE_SCRAP_SHARE = 0.015
STARTUP_SCRAP_SHARE = 0.08
STARTUP_MINUTES = 30

# Sensors.
NOISE_FRACTION = 0.03
ASSET_OFFSET_FRACTION = 0.05
IDLE_FRACTION = {"vibration": 0.05, "temperature": 0.35, "speed": 0.0, "pressure": 0.3, "current": 0.1}
SYMPTOM_GAIN = 1.5
# Wear share of the symptom window, raised to this power: the warning grows steadily and accelerates near failure.
WEAR_EXPONENT = 1.5
# Later symptoms start this share of the P-F interval after the first (spread evenly between them).
SYMPTOM_LAG_SHARE = 2.0 / 3.0
FALLING_SYMPTOMS = frozenset({("main_seal_leak", "hydraulic_pressure")})
COOLANT_SEASONAL_RISE = 1.0
# Scrap on the coolant story line starts rising above this coolant temperature (degrees C).
COOLANT_SCRAP_THRESHOLD = 24.0
SUMMER_PEAK_DAY_OF_YEAR = 200
GAP_SHARE = 0.003
OUTAGE_SENSOR_SHARE = 0.2
OUTAGE_HOURS = (6, 48)
SPIKE_SHARE = 0.0005
SPIKE_FACTOR = 10.0

# Historian tag suffix per sensor position.
SENSOR_CODES = {"spindle_vibration": "SPDL_VIB", "spindle_temperature": "SPDL_TMP", "spindle_speed": "SPDL_RPM",
                "coolant_temperature": "CLNT_TMP", "hydraulic_pressure": "HYD_PRS", "pressure_ripple": "HYD_RIP",
                "oil_temperature": "OIL_TMP", "motor_current": "MTR_AMP", "gearbox_vibration": "GBX_VIB",
                "motor_temperature": "MTR_TMP"}

# CMMS.
FAILURE_CODES = {"spindle_bearing_wear": "SPB-WEAR", "coolant_pump_cavitation": "CLP-CAV", "tool_changer_jam": "TCH-JAM",
                 "hydraulic_pump_wear": "HYP-WEAR", "main_seal_leak": "SEAL-LEAK", "gearbox_wear": "GBX-WEAR",
                 "motor_overheating": "MOT-HOT"}
FAILURE_TEXT = {"spindle_bearing_wear": "Spindle noisy and hot, replaced spindle bearing set",
                "coolant_pump_cavitation": "Coolant pump cavitating, replaced impeller",
                "tool_changer_jam": "Tool changer jammed, cleared magazine and re-referenced",
                "hydraulic_pump_wear": "Hydraulic pump worn, pressure unstable, pump replaced",
                "main_seal_leak": "Main seal leaking oil, seal kit replaced",
                "gearbox_wear": "Conveyor gearbox grinding, bearings and gears replaced",
                "motor_overheating": "Drive motor overheating, cleaned fins and tested windings"}
WORK_TYPE_CODES = {"corrective": "CM", "preventive": "PM", "instrument": "INST"}
CREATE_DELAY_MINUTES = (10, 40)
MISSING_CODE_SHARE = 0.15
LATE_CLOSE_SHARE = 0.3
LATE_CLOSE_DAYS = (1, 5)
DUPLICATE_SHARE = 0.05
DUPLICATE_DELAY_MINUTES = (5, 45)
PM_CREATE_LEAD_DAYS = 7
