"""Conforms master data: sites, lines, assets, components, sensors, products, and ideal cycle times.

Asset ids come from the asset numbering rule (site number, two-digit line, two-digit position), classes and sensors
from the catalog's labels, tag codes from the historian tag paths, and cycle times from either site's routing unit.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.source_layout import (
    ERP_ORDERS,
    ERP_PRODUCTS,
    REGISTER_ASSETS,
    REGISTER_SENSORS,
    Sources,
    routing_files,
)

LINE_PATTERN = r"^(?P<site>\S+) Line (?P<line>\d+)$"
TAG_SEPARATOR = "."
TAG_CODE_PART = 2
SECONDS_PER_HOUR = 3600.0
CYCLE_DECIMALS = 1
SENSOR_ID_SEPARATOR = "/"


def label_lookup(labels: dict[str, str], what: str) -> dict[str, str]:
    """Invert id -> label into label -> id, failing when two ids share a label."""
    inverted: dict[str, str] = {}
    for key, label in labels.items():
        if label in inverted:
            raise ConformError(f"Two {what} share the label '{label}'")
        inverted[label] = key
    return inverted


def conform_assets(sources: Sources, catalog: PlantCatalog, mappings: SourceMappings) -> pd.DataFrame:
    register = sources[REGISTER_ASSETS]
    classes = label_lookup({c.id: c.label for c in catalog.plant.asset_classes.values()}, "asset classes")
    unknown = sorted(set(register["EQUIPMENT_TYPE"]) - set(classes))
    if unknown:
        raise ConformError(f"{REGISTER_ASSETS}: unknown equipment types {unknown}")
    rows = []
    for row in register.itertuples():
        site = mappings.sites.get(row.SITE)
        if site is None:
            raise ConformError(f"{REGISTER_ASSETS}: unknown site '{row.SITE}'")
        line, position = int(row.LINE), int(str(row.ASSET_NO)[-2:])
        if str(row.ASSET_NO) != f"{site.number}{line:02d}{position:02d}":
            raise ConformError(f"{REGISTER_ASSETS}: asset number {row.ASSET_NO} does not follow site-line-position")
        line_id = f"{row.SITE}-L{line}"
        rows.append({"asset_id": f"{line_id}-{position:02d}", "line_id": line_id, "site_id": row.SITE,
                     "asset_class": classes[row.EQUIPMENT_TYPE], "position": position, "criticality": row.CRITICALITY,
                     "tag_code": _tag_code(sources, str(row.ASSET_NO)), "asset_number": str(row.ASSET_NO),
                     "workcenter": row.WORKCENTER, "nameplate_cycle_s": float(row.NAMEPLATE_CYCLE_S)})
    return pd.DataFrame(rows)


def _tag_code(sources: Sources, asset_number: str) -> str:
    tags = sources[REGISTER_SENSORS]
    codes = {tag.split(TAG_SEPARATOR)[TAG_CODE_PART] for tag in tags.loc[tags["ASSET_NO"] == asset_number, "TAG"]}
    if len(codes) != 1:
        raise ConformError(f"{REGISTER_SENSORS}: asset {asset_number} has tag codes {sorted(codes)}, expected exactly one")
    return codes.pop()


def conform_sensors(sources: Sources, assets: pd.DataFrame, catalog: PlantCatalog, mappings: SourceMappings) -> pd.DataFrame:
    tags = sources[REGISTER_SENSORS].merge(assets, left_on="ASSET_NO", right_on="asset_number", how="left")
    if tags["asset_id"].isna().any():
        raise ConformError(f"{REGISTER_SENSORS}: tags on unknown assets {sorted(tags.loc[tags['asset_id'].isna(), 'TAG'])}")
    rows = []
    for row in tags.itertuples():
        spec_class = catalog.plant.asset_classes[row.asset_class]
        by_label = label_lookup({s.id: s.label for s in spec_class.sensors.values()}, f"{row.asset_class} sensors")
        if row.MEASUREMENT not in by_label:
            raise ConformError(f"{REGISTER_SENSORS}: '{row.MEASUREMENT}' is not a {row.asset_class} sensor")
        spec = spec_class.sensors[by_label[row.MEASUREMENT]]
        unit = catalog.plant.sensor_types[spec.sensor_type].unit
        printed = mappings.printed_units.get(row.ENG_UNIT)
        if printed is None or printed.unit is not unit:
            raise ConformError(f"{REGISTER_SENSORS}: {row.TAG} is printed in '{row.ENG_UNIT}', which does not convert to {unit.value}")
        rows.append({"sensor_id": f"{row.asset_id}{SENSOR_ID_SEPARATOR}{spec.id}", "asset_id": row.asset_id, "sensor": spec.id,
                     "sensor_type": spec.sensor_type, "component": spec.component, "unit": unit.value,
                     "tag": row.TAG, "eng_unit": row.ENG_UNIT})
    return pd.DataFrame(rows)


def conform_sites(sensors: pd.DataFrame, assets: pd.DataFrame, mappings: SourceMappings) -> pd.DataFrame:
    converted = {text for text, u in mappings.printed_units.items() if u.scale != 1 or u.offset != 0}
    per_site = sensors.merge(assets[["asset_id", "site_id"]], on="asset_id").groupby("site_id")["eng_unit"].agg(set)
    return pd.DataFrame([{"site_id": s.site_id, "timezone": s.timezone, "imperial_units": bool(per_site.get(s.site_id, set()) & converted)}
                         for s in mappings.sites.values()])


def conform_components(assets: pd.DataFrame, catalog: PlantCatalog) -> pd.DataFrame:
    return pd.DataFrame([{"asset_id": a.asset_id, "component": c}
                         for a in assets.itertuples() for c in catalog.plant.asset_classes[a.asset_class].components])


def conform_products(sources: Sources) -> pd.DataFrame:
    return sources[ERP_PRODUCTS].rename(columns={"PRODUCT": "product_id", "FAMILY": "family"})[["product_id", "family"]]


def conform_lines(sources: Sources, assets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    orders = sources[ERP_ORDERS]
    parsed = orders["LINE"].str.extract(LINE_PATTERN)
    if parsed.isna().any().any():
        raise ConformError(f"{ERP_ORDERS}: line names not like '<site> Line <n>': {sorted(orders.loc[parsed['site'].isna(), 'LINE'].unique())}")
    families = pd.DataFrame({"line_id": parsed["site"] + "-L" + parsed["line"], "family": orders["PRODUCT"].map(products.set_index("product_id")["family"])})
    per_line = families.groupby("line_id")["family"].agg(set)
    if (per_line.map(len) != 1).any():
        raise ConformError(f"{ERP_ORDERS}: lines with more than one product family: {sorted(per_line[per_line.map(len) != 1].index)}")
    lines = assets.groupby("line_id", sort=True)["site_id"].first().reset_index()
    lines["line_number"] = lines["line_id"].str.split("-L").str[1].astype(int)
    lines["family"] = lines["line_id"].map(per_line.map(lambda f: next(iter(f))))
    return lines[["line_id", "site_id", "line_number", "family"]]


def conform_routings(sources: Sources, catalog: PlantCatalog) -> pd.DataFrame:
    classes = label_lookup({c.id: c.label for c in catalog.plant.asset_classes.values()}, "asset classes")
    frames = []
    for path in routing_files(sources):
        routing = sources[path]
        seconds = (SECONDS_PER_HOUR / routing["PARTS_PER_HOUR"]) if "PARTS_PER_HOUR" in routing else routing["CYCLE_SECONDS"]
        frames.append(pd.DataFrame({"product_id": routing["PRODUCT"], "asset_class": routing["EQUIPMENT_TYPE"].map(classes),
                                    "ideal_cycle_s": seconds.astype(float).round(CYCLE_DECIMALS)}))
    result = pd.concat(frames, ignore_index=True)
    if result["asset_class"].isna().any():
        raise ConformError("Routing rows with unknown equipment types")
    return result
