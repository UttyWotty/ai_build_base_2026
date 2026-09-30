"""The agent's tools as plain typed functions, which the Agent Development Kit turns into function declarations.

ADK reads each function's name, parameters, and docstring to describe the tool to the model, so the docstrings here are
written for the model. Each function delegates to CopilotTools and returns errors as data.
"""
from __future__ import annotations

from collections.abc import Callable

from copilot.services.agent_tools import CopilotTools


def adk_functions(tools: CopilotTools) -> list[Callable[..., dict[str, object]]]:
    """The tool functions bound to one run."""

    def list_open_alerts() -> dict:
        """List the failure alerts still waiting for a repair right now, earliest repair deadline first."""
        return tools.safe(tools.list_open_alerts)()

    def analyse_alert_impact(alert_id: str) -> dict:
        """Analyse one alert: spare stock at both sites, queued alerts, supplier record, every way to get the spare
        with its cost, downtime, lost contribution, worst case, and customer order lines at risk, plus the option the
        rules recommend."""
        return tools.safe(tools.analyse_alert_impact)(alert_id)

    def get_sensor_evidence(alert_id: str) -> dict:
        """Daily means of the sensors that react to the alert's failure mode over the last 7 days, with their normal
        ranges, the P-F interval, and the recommended repair action."""
        return tools.safe(tools.get_sensor_evidence)(alert_id)

    def get_field_reports(alert_id: str) -> dict:
        """Evidence from the field that Gemini has read: inspection photo findings for this alert, and supplier
        messages that changed delivery dates (already applied to the impact analysis)."""
        return tools.safe(tools.get_field_reports)(alert_id)

    def get_supplier_record(supplier_id: str) -> dict:
        """A supplier's on-time delivery (governed metric supplier_otd, with SQL fingerprint) and expected lateness in
        days over the last 90 days."""
        return tools.safe(tools.get_supplier_record)(supplier_id)

    def oee_summary(scope_type: str, scope_id: str, start: str, end: str) -> dict:
        """Availability, performance, quality, and OEE as fractions for a scope over [start, end) in ISO dates.
        scope_type is one of plant, site, line, asset; scope_id is e.g. US1, US1-L2, or US1-L2-01 (ignored for plant)."""
        return tools.safe(tools.oee_summary)(scope_type, scope_id, start, end)

    def failures(scope_type: str, scope_id: str, start: str, end: str) -> dict:
        """Equipment failures with their downtime in hours for a scope since start (ISO date), up to now."""
        return tools.safe(tools.failures)(scope_type, scope_id, start, end)

    def work_order_history(asset_id: str, start: str) -> dict:
        """Work orders of an asset created since start (ISO date), up to now."""
        return tools.safe(tools.work_order_history)(asset_id, start)

    def propose_action_plan(alert_id: str, option_kind: str, option_source: str, work_order_note: str,
                            customer_note: str) -> dict:
        """Create a proposal for a person to approve: the repair work order, the parts action given by option_kind and
        option_source (exactly as listed by analyse_alert_impact), and a note for the customers at risk (empty if
        none). Nothing is executed."""
        return tools.safe(tools.propose_action_plan)(alert_id, option_kind, option_source, work_order_note, customer_note)

    return [list_open_alerts, analyse_alert_impact, get_sensor_evidence, get_field_reports, get_supplier_record, oee_summary, failures,
            work_order_history, propose_action_plan]
