"""Reference mapping from ISO country code to the IANA time zone used to read local event dates.

The TMS and supplier portal record UTC timestamps; the ontology stores local dates, so conform needs each party's zone.
One zone per country is a documented simplification that holds for every country in the dataset.
"""
from __future__ import annotations

COUNTRY_TIMEZONES: dict[str, str] = {
    "US": "America/Chicago",
    "MX": "America/Monterrey",
    "DE": "Europe/Berlin",
    "PL": "Europe/Warsaw",
    "CN": "Asia/Shanghai",
    "JP": "Asia/Tokyo",
    "IN": "Asia/Kolkata",
}
