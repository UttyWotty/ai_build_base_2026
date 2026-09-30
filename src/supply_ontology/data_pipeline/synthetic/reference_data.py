"""Static reference data for the synthetic world: countries, plants, categories, carriers, and lead times.

Everything here is fictional and hand-written; nothing is derived from real companies.
Generators draw from these tables so the world has plausible geography, currencies, and time zones.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryProfile:
    """Region, invoicing currency, and time zone of a country."""

    region: str
    currency: str
    timezone: str


COUNTRIES: dict[str, CountryProfile] = {
    "US": CountryProfile("NA", "USD", "America/Chicago"),
    "MX": CountryProfile("NA", "MXN", "America/Monterrey"),
    "DE": CountryProfile("EU", "EUR", "Europe/Berlin"),
    "PL": CountryProfile("EU", "PLN", "Europe/Warsaw"),
    "CN": CountryProfile("APAC", "CNY", "Asia/Shanghai"),
    "JP": CountryProfile("APAC", "JPY", "Asia/Tokyo"),
    "IN": CountryProfile("APAC", "INR", "Asia/Kolkata"),
}

# Approximate starting USD value of one unit of each currency; the FX generator random-walks from here.
START_USD_PER_UNIT: dict[str, float] = {
    "USD": 1.0, "MXN": 0.055, "EUR": 1.08, "PLN": 0.25, "CNY": 0.14, "JPY": 0.0068, "INR": 0.012,
}


@dataclass(frozen=True)
class PlantProfile:
    """A fictional plant."""

    plant_id: str
    plant_name: str
    country: str


PLANTS: tuple[PlantProfile, ...] = (
    PlantProfile("US01", "Lakeside Distribution Center", "US"),
    PlantProfile("MX01", "Norte Assembly Plant", "MX"),
    PlantProfile("DE01", "Rhein Valley Plant", "DE"),
    PlantProfile("CN01", "Delta Components Plant", "CN"),
)

# Supplier and customer country mixes (weights need not sum to one; they are normalized).
SUPPLIER_COUNTRY_WEIGHTS: dict[str, float] = {"US": 5, "MX": 3, "DE": 5, "PL": 3, "CN": 8, "JP": 3, "IN": 3}
CUSTOMER_COUNTRY_WEIGHTS: dict[str, float] = {"US": 6, "MX": 3, "DE": 5, "PL": 2, "CN": 4, "JP": 2, "IN": 2}

COMPANY_SUFFIX: dict[str, str] = {
    "US": "Inc.", "MX": "S.A. de C.V.", "DE": "GmbH", "PL": "Sp. z o.o.",
    "CN": "Co., Ltd.", "JP": "K.K.", "IN": "Pvt. Ltd.",
}
SUPPLIER_NAME_STEMS: tuple[str, ...] = (
    "Apex", "Borealis", "Cobalt", "Dynaform", "Everline", "Fulcrum", "Granite", "Helix", "Ironwood", "Juniper",
    "Keystone", "Lumen", "Meridian", "Northgate", "Orbital", "Pinnacle", "Quarry", "Redwood", "Summit", "Tidewater",
)
SUPPLIER_NAME_TRADES: tuple[str, ...] = ("Industrial", "Precision", "Components", "Manufacturing", "Metalworks")
CUSTOMER_NAME_STEMS: tuple[str, ...] = (
    "Atlas", "Beacon", "Crescent", "Delta", "Ember", "Falcon", "Harbor", "Horizon", "Kestrel", "Legacy",
    "Monarch", "Nova", "Osprey", "Prairie", "Radiant", "Sterling", "Trident", "Vanguard", "Willow", "Zenith",
)
CUSTOMER_NAME_TRADES: tuple[str, ...] = (
    "Machinery", "Motors", "Equipment", "Systems", "Supply", "Dynamics", "Logistics",
)

SEGMENTS: tuple[str, ...] = ("OEM", "Distributor", "Aftermarket")
SEGMENT_WEIGHTS: tuple[float, ...] = (0.45, 0.35, 0.20)

# Category -> (families, standard cost range in USD).
CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[float, float]]] = {
    "Bearings": (("Ball bearings", "Roller bearings", "Plain bearings"), (2.0, 45.0)),
    "Fasteners": (("Bolts", "Nuts", "Rivets"), (0.05, 1.5)),
    "Electrical": (("Connectors", "Relays", "Harnesses"), (1.0, 60.0)),
    "Hydraulics": (("Valves", "Hoses", "Fittings"), (4.0, 120.0)),
    "Packaging": (("Cartons", "Pallets", "Stretch film"), (0.3, 12.0)),
    "Castings": (("Housings", "Brackets", "Flanges"), (6.0, 90.0)),
}
# Packaging parts move in cases; the TMS reports their quantities in cases of this size.
CASE_PACKED_CATEGORY = "Packaging"
CASE_PACK_SIZES: tuple[int, ...] = (10, 20, 50)
EACH_UOM = "EA"
CASE_UOM = "CS"

MOQ_CHOICES: tuple[int, ...] = (10, 25, 50, 100)
# Contracted lead time range in days by supplier region.
LEAD_TIME_DAYS_BY_REGION: dict[str, tuple[int, int]] = {"NA": (7, 21), "EU": (10, 28), "APAC": (35, 56)}

# Nominal transit days by lane class, and the matching freight base cost per shipment in USD.
DOMESTIC, REGIONAL, INTERCONTINENTAL = "domestic", "regional", "intercontinental"
TRANSIT_DAYS: dict[str, int] = {DOMESTIC: 2, REGIONAL: 5, INTERCONTINENTAL: 28}
FREIGHT_BASE_USD: dict[str, float] = {DOMESTIC: 180.0, REGIONAL: 520.0, INTERCONTINENTAL: 2400.0}
# Goods value of a full load per lane class; smaller shipments pay a proportional share of the base, never below the minimum share.
FULL_LOAD_VALUE_USD: dict[str, float] = {DOMESTIC: 3000.0, REGIONAL: 8000.0, INTERCONTINENTAL: 30000.0}
MIN_LOAD_SHARE = 0.15

# Carrier codes by region, plus ocean carriers for intercontinental lanes, with their on-time share.
CARRIERS_BY_REGION: dict[str, tuple[str, ...]] = {
    "NA": ("MWTL", "SWFT", "RDWY"), "EU": ("RHNF", "KNXL", "DSVE"), "APAC": ("SFXP", "YTOL", "ZTOE"),
}
OCEAN_CARRIERS: tuple[str, ...] = ("OCNA", "OCNB")
CARRIER_ON_TIME_SHARE: dict[str, float] = {
    "MWTL": 0.93, "SWFT": 0.88, "RDWY": 0.91, "RHNF": 0.94, "KNXL": 0.90, "DSVE": 0.86,
    "SFXP": 0.92, "YTOL": 0.87, "ZTOE": 0.89, "OCNA": 0.82, "OCNB": 0.78,
}


def lane_class(origin_country: str, destination_country: str) -> str:
    """Classify a lane as domestic, regional, or intercontinental."""
    if origin_country == destination_country:
        return DOMESTIC
    if COUNTRIES[origin_country].region == COUNTRIES[destination_country].region:
        return REGIONAL
    return INTERCONTINENTAL
