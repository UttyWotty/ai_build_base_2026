"""Renders reference feeds: treasury FX rates, the trade compliance duty table, and the MDM partner crosswalk.

Treasury quotes currency units per USD and trade quotes duty in percent, the inverse and a hundredfold of the canonical values.
The crosswalk is the only bridge from TMS partner codes to ERP numbers, as in a real master data hub.
"""
from __future__ import annotations

from supply_ontology.data_pipeline.synthetic.source_file import FileFormat, SourceFile
from supply_ontology.data_pipeline.synthetic.world_tables import WorldExtras


def render_reference(extras: WorldExtras) -> list[SourceFile]:
    """Return FX, duty, and crosswalk files."""
    fx = extras.fx_published.rename(columns={"rate_date": "Date", "currency": "Currency", "units_per_usd": "Rate per USD"})
    duty = extras.duty_published.rename(columns={"origin_country": "Origin", "category": "Category", "duty_rate_pct": "Duty %"})
    crosswalk = extras.partner_codes.rename(
        columns={"partner_code": "PARTNER_CODE", "partner_type": "PARTNER_TYPE", "canonical_id": "ERP_NUMBER"}
    )
    return [
        SourceFile("treasury/fx_rates.xlsx", fx[["Date", "Currency", "Rate per USD"]], FileFormat.XLSX),
        SourceFile("trade/duty_rates.xlsx", duty, FileFormat.XLSX),
        SourceFile("mdm/partner_crosswalk.xlsx", crosswalk, FileFormat.XLSX),
    ]
