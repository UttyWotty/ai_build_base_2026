"""Renders the ERP: products, per-site routings with ideal speed in each site's convention, and production orders.

US1 states ideal speed in parts per hour, DE1 in seconds per part; conform converts both to seconds per part.
Orders name their line as "<site> Line <n>" and carry local planned start and end times.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.plant_model import PlantModel
from pdm_oee.data_pipeline.synthetic.local_time import to_local
from pdm_oee.data_pipeline.synthetic.source_file import FileFormat, SourceFile

SECONDS_PER_HOUR = 3600.0
RATE_DECIMALS = 4
PER_HOUR_SITES = frozenset({"US1"})


def render_erp(tables: dict[str, pd.DataFrame], plant: PlantModel) -> list[SourceFile]:
    lines, products = tables["line"], tables["product"]
    files = [SourceFile("erp/products.xlsx", products.rename(columns={"product_id": "PRODUCT", "family": "FAMILY"}), FileFormat.XLSX)]
    for site_id in sorted(lines["site_id"].unique()):
        families = set(lines.loc[lines["site_id"] == site_id, "family"])
        routing = tables["routing"].merge(products, on="product_id")
        routing = routing[routing["family"].isin(families)]
        frame = pd.DataFrame({"PRODUCT": routing["product_id"],
                              "EQUIPMENT_TYPE": [plant.asset_classes[c].label for c in routing["asset_class"]]})
        if site_id in PER_HOUR_SITES:
            frame["PARTS_PER_HOUR"] = (SECONDS_PER_HOUR / routing["ideal_cycle_s"]).round(RATE_DECIMALS).to_numpy()
        else:
            frame["CYCLE_SECONDS"] = routing["ideal_cycle_s"].to_numpy()
        files.append(SourceFile(f"erp/routings_{site_id}.xlsx", frame.reset_index(drop=True), FileFormat.XLSX))
    orders = tables["production_order"].merge(lines, on="line_id")
    files.append(SourceFile("erp/production_orders.xlsx", pd.DataFrame({
        "ORDER_NO": orders["order_id"], "LINE": [f"{s} Line {n}" for s, n in zip(orders["site_id"], orders["line_number"])],
        "PRODUCT": orders["product_id"], "QTY": orders["quantity"],
        "START_LOCAL": to_local(orders["planned_start_at"], orders["site_id"]),
        "END_LOCAL": to_local(orders["planned_end_at"], orders["site_id"])}), FileFormat.XLSX))
    return files
