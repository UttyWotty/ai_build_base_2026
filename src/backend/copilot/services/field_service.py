"""Reads field inputs with Gemini and keeps them: inspection photos for alerts, and supplier messages about deliveries.

An inspection is read against the alert's failure mode, so Gemini judges the photo with the right question in mind.
A supplier message becomes an update that revises the matching open order from the moment it was received, which the
impact analysis picks up at once. Gemini reads run in a worker thread, so a slow read never stalls other visitors.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from copilot.core.errors import ImpactError
from copilot.core.field_inputs import (
    INSPECTION_SCHEMA,
    SUPPLIER_INSTRUCTION,
    SUPPLIER_SCHEMA,
    InspectionFinding,
    SupplierUpdate,
    inspection_instruction,
    parse_inspection,
    parse_supplier_update,
)
from copilot.data_pipeline.record_store import RecordStore
from copilot.services.alert_book import AlertBook
from llm_gateway.multimodal import Attachment, StructuredReader
from pdm_oee.core.catalog import PlantCatalog


def _ts(value: object) -> datetime | None:
    return None if value in (None, "", "None") else pd.Timestamp(str(value)).to_pydatetime()


@dataclass(frozen=True)
class InspectionTask:
    """An alert checked and ready for Gemini: the instruction that frames the photo for its failure mode."""

    alert_id: str
    asset_id: str
    instruction: str


class FieldInputService:
    """Inspection findings and supplier updates."""

    def __init__(self, reader: StructuredReader, alerts: AlertBook, plant_catalog: PlantCatalog,
                 inspections: RecordStore, updates: RecordStore) -> None:
        self.reader = reader
        self.alerts = alerts
        self.plant_catalog = plant_catalog
        self.inspections = inspections
        self.updates = updates

    def prepare_inspection(self, alert_id: str) -> InspectionTask:
        """Checks the alert and builds the instruction; raises ImpactError before any Gemini call is spent."""
        alert = self.alerts.get(alert_id)
        mode = next((c.failure_modes[alert.failure_mode] for c in self.plant_catalog.plant.asset_classes.values()
                     if alert.failure_mode in c.failure_modes), None)
        if mode is None:
            raise ImpactError(f"No failure mode {alert.failure_mode} in the plant catalog")
        symptoms = ", ".join(s.replace("_", " ") for s in mode.symptoms) or "its history"
        instruction = inspection_instruction(alert.asset_id, mode.label, mode.component, symptoms, mode.recommended_action)
        return InspectionTask(alert.alert_id, alert.asset_id, instruction)

    async def inspect(self, task: InspectionTask, photo: Attachment, received_at: datetime) -> InspectionFinding:
        raw = await asyncio.to_thread(self.reader.read, task.instruction, "", [photo], INSPECTION_SCHEMA)
        finding = parse_inspection(raw, task.alert_id, task.asset_id, received_at)
        self.inspections.add(finding)
        return finding

    async def read_supplier_message(self, text: str, attachments: list[Attachment],
                                    received_at: datetime) -> SupplierUpdate:
        raw = await asyncio.to_thread(self.reader.read, SUPPLIER_INSTRUCTION, text, attachments, SUPPLIER_SCHEMA)
        update = parse_supplier_update(raw, received_at)
        self.updates.add(update)
        return update

    def findings_for(self, alert_id: str, now: datetime) -> list[dict[str, object]]:
        return [r for r in self.inspections.all() if r["alert_id"] == alert_id and (_ts(r["received_at"]) or now) <= now]

    def supplier_updates(self) -> list[SupplierUpdate]:
        return [SupplierUpdate(_ts(r["received_at"]) or datetime.min, str(r["supplier_name"]), str(r["order_reference"]),
                               str(r["change"]), _ts(r["new_delivery_at"]), str(r["reason"]), float(r["confidence"]))
                for r in self.updates.all()]

    def updates_known(self, now: datetime) -> list[SupplierUpdate]:
        return [u for u in self.supplier_updates() if u.received_at <= now]
