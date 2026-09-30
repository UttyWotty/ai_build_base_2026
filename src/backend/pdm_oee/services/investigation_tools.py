"""The investigation tools: deterministic queries behind each governed tool name, returning compact JSON-ready results.

Ratios are returned as fractions with four decimals and durations in hours with one, so an answer quoting "82.3%" or
"12.5 h" can be checked against them. Long series are shortened to weekly values so results stay small; a call the
data cannot answer raises ToolError with a message meant for the model.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.sensor_hours import running_readings
from pdm_oee.core.tool_catalog import TOOLS
from pdm_oee.services.oee_service import OEEService

RATIO_DECIMALS, HOUR_DECIMALS, VALUE_DECIMALS = 4, 1, 2
MINUTES_PER_HOUR = 60
FACTORS = ("availability", "performance", "quality", "oee")
SCOPE_COLUMN = {"site": "site_id", "line": "line_id", "asset": "asset_id"}
GRAIN_COLUMN = {"day": "shift_date", "week": "week", "month": "month"}
MAX_ROWS = 40
DEFAULT_LIMIT = 5
TEMPERATURE_TYPE = "temperature"
READINGS_SQL = "SELECT sensor_id, ts, value, quality FROM sensor_reading WHERE sensor_id IN ({marks}) AND ts >= ? AND ts < ?"


class ToolError(Exception):
    """A valid call that the data cannot answer; the message is sent back to the model."""


class ToolBox:
    """Runs validated tool calls against the OEE service, the conformed tables, and the alert replay."""

    def __init__(self, catalog: PlantCatalog, oee: OEEService, alerts: list[dict]) -> None:
        self.catalog, self.oee, self.alert_records = catalog, oee, pd.DataFrame(alerts)
        tables = oee.tables
        self.assets = tables["asset"]
        self.sensors = oee.connection_manager.execute("SELECT * FROM sensor")
        self.handlers: dict[str, Callable[..., object]] = {t.name: getattr(self, t.name) for t in TOOLS}

    def vocabularies(self) -> dict[str, list[str]]:
        return {"scope_type": ["plant", *SCOPE_COLUMN], "plant": ["plant"], "site": sorted(self.assets["site_id"].unique()),
                "line": sorted(self.assets["line_id"].unique()), "asset": sorted(self.assets["asset_id"]),
                "sensor": sorted(self.sensors["sensor"].unique()), "loss": list(self.catalog.losses.losses),
                "grain": list(GRAIN_COLUMN), "group": ["asset", "line"]}

    def run(self, tool: str, arguments: dict) -> object:
        return self.handlers[tool](**arguments)

    def _filters(self, scope_type: str, scope_id: str) -> dict[str, str]:
        return {} if scope_type == "plant" else {SCOPE_COLUMN[scope_type]: scope_id}

    def oee_summary(self, scope_type: str, scope_id: str, start: date, end: date) -> dict:
        row = self.oee.metrics(FACTORS, [], start, end, self._filters(scope_type, scope_id)).iloc[0]
        return {f: _ratio(row[f]) for f in FACTORS}

    def oee_trend(self, scope_type: str, scope_id: str, start: date, end: date, grain: str) -> list[dict]:
        table = self.oee.metrics(FACTORS, [GRAIN_COLUMN[grain]], start, end, self._filters(scope_type, scope_id)).tail(MAX_ROWS)
        return [{"period": str(r[GRAIN_COLUMN[grain]]), **{f: _ratio(r[f]) for f in FACTORS}} for _, r in table.iterrows()]

    def loss_breakdown(self, scope_type: str, scope_id: str, start: date, end: date) -> list[dict]:
        steps = self.oee.loss_waterfall(start, end, self._filters(scope_type, scope_id))
        return [{"step": s, "hours": round(abs(m) / MINUTES_PER_HOUR, HOUR_DECIMALS)} for s, m in zip(steps["step"], steps["minutes"])]

    def top_loss_contributors(self, loss: str, group: str, start: date, end: date, limit: int = DEFAULT_LIMIT) -> list[dict]:
        rows = self.oee.period(start, end)
        column = SCOPE_COLUMN[group]
        frame = self.oee.losses[rows].assign(**{column: self.oee.measures.loc[rows, column].to_numpy()})
        totals = (frame.groupby(column)[loss].sum() / MINUTES_PER_HOUR).sort_values(ascending=False).head(limit)
        return [{group: key, "hours": round(float(v), HOUR_DECIMALS)} for key, v in totals.items()]

    def sensor_trend(self, asset_id: str, sensor: str, start: date, end: date) -> dict:
        spec = self._sensor_spec(asset_id, sensor)
        running = self._running([f"{asset_id}/{sensor}"], start, end)
        grain = "D" if (end - start).days <= MAX_ROWS else "W"
        series = running.set_index("ts")["value"].resample(grain).mean().dropna().round(VALUE_DECIMALS)
        return {"sensor": sensor, "label": spec.label, "unit": self.catalog.plant.sensor_types[spec.sensor_type].unit.value,
                "normal_range": list(spec.normal_range), "grain": "day" if grain == "D" else "week",
                "values": [{"period": str(k.date()), "mean": float(v)} for k, v in series.tail(MAX_ROWS).items()]}

    def failures(self, scope_type: str, scope_id: str, start: date, end: date) -> dict:
        events = self.oee.tables["failure_event"].merge(self.assets[["asset_id", "line_id", "site_id"]], on="asset_id")
        mine = events[(events["failed_at"] >= pd.Timestamp(start)) & (events["failed_at"] < pd.Timestamp(end))]
        for column, value in self._filters(scope_type, scope_id).items():
            mine = mine[mine[column] == value]
        rows = [{"asset_id": f.asset_id, "failure_mode": f.failure_mode, "failed_at": str(f.failed_at),
                 "downtime_hours": round((f.restored_at - f.failed_at) / pd.Timedelta(hours=1), HOUR_DECIMALS)} for f in mine.itertuples()]
        return {"count": len(rows), "failures": rows[:MAX_ROWS]}

    def work_order_history(self, asset_id: str, start: date, end: date) -> list[dict]:
        orders = self.oee.tables["work_order"]
        mine = orders[(orders["asset_id"] == asset_id) & (orders["created_at"] >= pd.Timestamp(start)) & (orders["created_at"] < pd.Timestamp(end))]
        return [{"wo_id": o.wo_id, "type": o.work_type, "failure_mode": o.failure_mode, "created_at": str(o.created_at),
                 "closed_at": str(o.closed_at), "description": o.description} for o in mine.tail(MAX_ROWS).itertuples()]

    def alerts(self, scope_type: str, scope_id: str, start: date, end: date) -> dict:
        if self.alert_records.empty:
            return {"count": 0, "alerts": []}
        raised = pd.to_datetime(self.alert_records["raised_at"])
        mine = self.alert_records[(raised >= pd.Timestamp(start)) & (raised < pd.Timestamp(end))].merge(self.assets[["asset_id", "line_id", "site_id"]], on="asset_id")
        for column, value in self._filters(scope_type, scope_id).items():
            mine = mine[mine[column] == value]
        keep = ["alert_id", "asset_id", "failure_mode", "raised_at", "priority", "outcome", "truth"]
        return {"count": len(mine), "alerts": mine[keep].head(MAX_ROWS).to_dict("records")}

    def quality_drivers(self, line_id: str, start: date, end: date) -> dict:
        rows = self.oee.period(start, end) & (self.oee.measures["line_id"] == line_id)
        weekly = self.oee.measures[rows].groupby("week")[["good_count", "total_count"]].sum()
        quality = (weekly["good_count"] / weekly["total_count"]).rename("quality")
        temps = self.sensors[(self.sensors["asset_id"].isin(self.assets.loc[self.assets["line_id"] == line_id, "asset_id"]))
                             & (self.sensors["sensor_type"] == TEMPERATURE_TYPE)]
        running = self._running(list(temps["sensor_id"]), start, end)
        running["week"] = running["ts"].dt.strftime("%G-W%V")
        means = running.pivot_table(index="week", columns="sensor_id", values="value", aggfunc="mean")
        joined = means.join(quality, how="inner")
        correlations = {s: round(float(joined[s].corr(joined["quality"])), VALUE_DECIMALS) for s in means.columns if joined[s].notna().sum() > 2}
        return {"weeks": len(joined), "correlation_with_quality": dict(sorted(correlations.items(), key=lambda kv: kv[1])),
                "weekly_quality": {w: _ratio(q) for w, q in quality.tail(MAX_ROWS).items()}}

    def _sensor_spec(self, asset_id: str, sensor: str) -> object:
        asset_class = self.assets.set_index("asset_id").loc[asset_id, "asset_class"]
        sensors = self.catalog.plant.asset_classes[asset_class].sensors
        if sensor not in sensors:
            raise ToolError(f"Asset {asset_id} is a {asset_class}; its sensors are {', '.join(sensors)}")
        return sensors[sensor]

    def _running(self, sensor_ids: list[str], start: date, end: date) -> pd.DataFrame:
        if not sensor_ids:
            return pd.DataFrame(columns=["sensor_id", "asset_id", "sensor", "ts", "value"])
        sql = READINGS_SQL.format(marks=", ".join("?" for _ in sensor_ids))
        readings = self.oee.connection_manager.execute(sql, [*sensor_ids, pd.Timestamp(start), pd.Timestamp(end)])
        return running_readings(readings, self.sensors, self.oee.tables["machine_state"])


def _ratio(value: float) -> float | None:
    return None if pd.isna(value) else round(float(value), RATIO_DECIMALS)
